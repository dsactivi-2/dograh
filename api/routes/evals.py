"""Eval harness API — text (P2) + voice score/sessions (P6)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from pipecat.utils.run_context import set_current_run_id

from api.db import db_client
from api.db.models import UserModel
from api.enums import WorkflowRunMode
from api.schemas.text_eval import TextEvalRunResponse, TextEvalScenario
from api.schemas.voice_eval import (
    VoiceScoreRunRequest,
    VoiceScoreRunResponse,
    VoiceSessionCreateRequest,
    VoiceSessionCreateResponse,
    VoiceSessionFinalizeRequest,
    VoiceSessionFinalizeResponse,
)
from api.services.auth.depends import get_user
from api.services.evals.text_harness import run_text_eval_scenario
from api.services.evals.voice_guards import (
    VoiceEvalGuardError,
    check_voice_eval_allowed,
    clamp_max_duration_seconds,
    http_status_for_guard,
    public_guard_config,
    voice_eval_guard_payload,
)
from api.services.evals.voice_score import score_voice_run
from api.services.quota_service import authorize_workflow_run_start
from api.services.workflow.run_creation import prepare_workflow_run_inputs
from api.services.workflow.text_chat_session_service import (
    TextChatSessionExecutionError,
    TextChatSessionRevisionConflictError,
    append_text_chat_user_message,
    default_text_chat_checkpoint,
    default_text_chat_session_data,
    execute_pending_text_chat_turn,
    initialize_text_chat_session,
    normalize_text_chat_session_data,
)

router = APIRouter(prefix="/evals", tags=["evals"])


def _require_org(user: UserModel) -> int:
    if not user.selected_organization_id:
        raise HTTPException(status_code=400, detail="No organization selected")
    return int(user.selected_organization_id)


def _assistant_from_session(session_data: dict[str, Any]) -> str:
    """Best-effort last assistant message from text-chat session_data."""
    data = normalize_text_chat_session_data(session_data)
    turns = data.get("turns") or []
    if not isinstance(turns, list):
        return ""
    for t in reversed(turns):
        if not isinstance(t, dict):
            continue
        am = t.get("assistant_message")
        if isinstance(am, dict) and am.get("text"):
            return str(am["text"])
        if t.get("assistant_text"):
            return str(t["assistant_text"])
        role = str(t.get("role") or t.get("speaker") or "").lower()
        if role in ("assistant", "agent", "bot", "ai"):
            return str(t.get("text") or t.get("content") or t.get("message") or "")
    return str(data.get("last_assistant_text") or "")


@router.get("/health")
async def evals_health():
    return {
        "status": "ok",
        "module": "evals",
        "harness": ["text-chat", "voice-score", "voice-session"],
        "voice": {
            "score_run": True,
            "create_session": True,
            "headless_audio": False,
            "dual_role": False,
            "guards": public_guard_config(),
        },
    }


@router.get("/voice/guards")
async def voice_eval_guards_status(user: UserModel = Depends(get_user)):
    """Current org rate-limit status + static guard config (dashboard-friendly)."""
    org_id = _require_org(user)
    recent = await db_client.count_recent_voice_eval_sessions(org_id, hours=1)
    cfg = public_guard_config()
    try:
        live = check_voice_eval_allowed(recent_session_count=recent, batch_size=1)
        return {
            "organization_id": org_id,
            "allowed": True,
            "recent_session_count": recent,
            **cfg,
            **{k: live[k] for k in ("remaining_after",) if k in live},
        }
    except VoiceEvalGuardError as e:
        return {
            "organization_id": org_id,
            "allowed": False,
            "code": e.code,
            "message": e.message,
            "recent_session_count": recent,
            **cfg,
        }


@router.post("/text/run", response_model=TextEvalRunResponse)
async def run_text_eval(
    scenario: TextEvalScenario,
    user: UserModel = Depends(get_user),
) -> TextEvalRunResponse:
    """Run a text-chat eval scenario against a workflow (creates a TEXTCHAT run)."""
    org_id = _require_org(user)
    workflow_id = scenario.workflow_id

    workflow = await db_client.get_workflow(workflow_id, organization_id=org_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    async def create_session(wf_id: int, initial_context: dict[str, Any]):
        run_inputs = await prepare_workflow_run_inputs(
            db_client,
            workflow,
            initial_context=initial_context or {},
            use_draft=True,
            include_template_context=True,
        )
        name = f"EVAL-{uuid4().hex[:8].upper()}"
        workflow_run = await db_client.create_workflow_run(
            name=name,
            workflow_id=wf_id,
            mode=WorkflowRunMode.TEXTCHAT.value,
            user_id=user.id,
            initial_context=run_inputs.initial_context,
            organization_id=org_id,
            definition_id=run_inputs.definition_id,
        )
        set_current_run_id(workflow_run.id)

        quota = await authorize_workflow_run_start(
            workflow_id=wf_id,
            organization_id=org_id,
            workflow_run_id=workflow_run.id,
            actor_user=user,
        )
        if not quota.has_quota:
            raise HTTPException(status_code=402, detail=quota.error_message)

        annotations = {
            "tester": {"source": "text_eval_harness", "modality": "text"},
            "eval": {"scenario_name": scenario.name},
        }
        await db_client.update_workflow_run(workflow_run.id, annotations=annotations)

        text_session = await db_client.ensure_workflow_run_text_session(
            workflow_run.id,
            session_data=default_text_chat_session_data(),
            checkpoint=default_text_chat_checkpoint(),
        )
        try:
            text_session = await initialize_text_chat_session(
                run_id=workflow_run.id,
                text_session=text_session,
            )
            text_session = await execute_pending_text_chat_turn(
                workflow_id=wf_id,
                run_id=workflow_run.id,
                text_session=text_session,
            )
        except (TextChatSessionRevisionConflictError, TextChatSessionExecutionError) as e:
            logger.warning(f"eval session init issue: {e}")

        return {"workflow_run_id": workflow_run.id}

    async def execute_turn(run_id: int, text: str):
        text_session = await db_client.get_workflow_run_text_session(
            run_id, organization_id=org_id
        )
        if not text_session:
            raise RuntimeError("text session missing")

        quota = await authorize_workflow_run_start(
            workflow_id=workflow_id,
            organization_id=org_id,
            workflow_run_id=run_id,
            actor_user=user,
        )
        if not quota.has_quota:
            raise HTTPException(status_code=402, detail=quota.error_message)

        text_session = await append_text_chat_user_message(
            run_id=run_id,
            text_session=text_session,
            user_text=text,
            expected_revision=None,
        )
        text_session = await execute_pending_text_chat_turn(
            workflow_id=workflow_id,
            run_id=run_id,
            text_session=text_session,
        )
        run = await db_client.get_workflow_run(run_id, organization_id=org_id)
        gathered = (run.gathered_context if run else {}) or {}
        assistant = _assistant_from_session(text_session.session_data or {})
        return {"assistant_text": assistant, "gathered_context": gathered}

    return await run_text_eval_scenario(
        scenario=scenario,
        organization_id=org_id,
        user_id=user.id,
        execute_turn=execute_turn,
        create_session=create_session,
    )


@router.post("/voice/score-run", response_model=VoiceScoreRunResponse)
async def voice_score_run(
    body: VoiceScoreRunRequest,
    user: UserModel = Depends(get_user),
) -> VoiceScoreRunResponse:
    """Score an existing voice (or any) run from transcript + disposition + QA."""
    org_id = _require_org(user)
    run = await db_client.get_workflow_run(
        body.workflow_run_id, organization_id=org_id
    )
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    scored = score_voice_run(
        run_id=run.id,
        workflow_id=run.workflow_id,
        mode=run.mode,
        is_completed=bool(run.is_completed),
        logs=run.logs,
        gathered_context=run.gathered_context,
        annotations=run.annotations,
        assertions=body.assertions,
        success_codes=body.success_codes,
        pass_score=body.pass_score,
        include_qa=body.include_qa,
    )
    # Persist score stamp on annotations for QA Center / Scripts links
    try:
        await db_client.update_workflow_run(
            run.id,
            annotations={
                "voice_eval": {
                    "score": scored["score"],
                    "passed": scored["passed"],
                    "scored_by_user_id": int(user.id),
                    "source": "evals.voice.score-run",
                }
            },
        )
    except Exception as e:
        logger.warning(f"voice score annotation write failed: {e}")

    return VoiceScoreRunResponse(**scored)


@router.post("/voice/sessions", response_model=VoiceSessionCreateResponse)
async def create_voice_eval_session(
    body: VoiceSessionCreateRequest,
    user: UserModel = Depends(get_user),
) -> VoiceSessionCreateResponse:
    """Create a SHORT SMALLWEBRTC run for human-in-the-loop voice eval.

    Does NOT start audio itself — client connects via existing WebRTC signaling.
    Cost guards: rate limit per org/hour, batch=1, duration hint.
    """
    org_id = _require_org(user)
    recent = await db_client.count_recent_voice_eval_sessions(org_id, hours=1)
    try:
        guards = check_voice_eval_allowed(recent_session_count=recent, batch_size=1)
    except VoiceEvalGuardError as e:
        raise HTTPException(
            status_code=http_status_for_guard(e.code),
            detail={"code": e.code, "message": e.message},
        ) from e

    workflow = await db_client.get_workflow(body.workflow_id, organization_id=org_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    max_dur = clamp_max_duration_seconds(body.max_duration_seconds)
    run_inputs = await prepare_workflow_run_inputs(
        db_client,
        workflow,
        initial_context=body.initial_context or {},
        use_draft=True,
        include_template_context=True,
    )
    name = f"VEVAL-{uuid4().hex[:8].upper()}"
    workflow_run = await db_client.create_workflow_run(
        name=name,
        workflow_id=body.workflow_id,
        mode=WorkflowRunMode.SMALLWEBRTC.value,
        user_id=user.id,
        initial_context=run_inputs.initial_context,
        organization_id=org_id,
        definition_id=run_inputs.definition_id,
    )
    set_current_run_id(workflow_run.id)

    quota = await authorize_workflow_run_start(
        workflow_id=body.workflow_id,
        organization_id=org_id,
        workflow_run_id=workflow_run.id,
        actor_user=user,
    )
    if not quota.has_quota:
        raise HTTPException(status_code=402, detail=quota.error_message)

    guard_meta = voice_eval_guard_payload(
        recent_session_count=recent,
        max_duration_seconds=max_dur,
    )
    await db_client.update_workflow_run(
        workflow_run.id,
        annotations={
            "tester": guard_meta,
            "eval": {
                "scenario_name": body.scenario_name,
                "assertions": body.assertions,
                "success_codes": body.success_codes,
                "pass_score": body.pass_score,
                "script_entry_id": body.script_entry_id,
                "tags": body.tags,
            },
        },
        initial_context={
            "voice_eval": {
                "scenario_name": body.scenario_name,
                "max_duration_hint_seconds": max_dur,
            }
        },
    )

    signaling = f"/api/v1/ws/signaling/{body.workflow_id}/{workflow_run.id}"
    return VoiceSessionCreateResponse(
        workflow_id=body.workflow_id,
        workflow_run_id=workflow_run.id,
        mode=WorkflowRunMode.SMALLWEBRTC.value,
        scenario_name=body.scenario_name,
        max_duration_hint_seconds=max_dur,
        signaling_path=signaling,
        guards=guards,
        assertions=body.assertions,
        success_codes=body.success_codes,
        pass_score=body.pass_score,
    )


@router.post(
    "/voice/sessions/{run_id}/finalize",
    response_model=VoiceSessionFinalizeResponse,
)
async def finalize_voice_eval_session(
    run_id: int,
    body: VoiceSessionFinalizeRequest | None = None,
    user: UserModel = Depends(get_user),
) -> VoiceSessionFinalizeResponse:
    """Score a voice-eval session after the WebRTC call ends."""
    org_id = _require_org(user)
    body = body or VoiceSessionFinalizeRequest()
    run = await db_client.get_workflow_run(run_id, organization_id=org_id)
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    ann = run.annotations if isinstance(run.annotations, dict) else {}
    eval_meta = ann.get("eval") if isinstance(ann.get("eval"), dict) else {}
    assertions = body.assertions or eval_meta.get("assertions") or []
    success_codes = body.success_codes or eval_meta.get("success_codes") or []
    pass_score = (
        body.pass_score
        if body.pass_score is not None
        else float(eval_meta.get("pass_score") or 70)
    )

    scored = score_voice_run(
        run_id=run.id,
        workflow_id=run.workflow_id,
        mode=run.mode,
        is_completed=bool(run.is_completed),
        logs=run.logs,
        gathered_context=run.gathered_context,
        annotations=run.annotations,
        assertions=assertions,
        success_codes=success_codes,
        pass_score=pass_score,
        include_qa=body.include_qa,
    )
    try:
        await db_client.update_workflow_run(
            run.id,
            annotations={
                "voice_eval": {
                    "score": scored["score"],
                    "passed": scored["passed"],
                    "scored_by_user_id": int(user.id),
                    "source": "evals.voice.finalize",
                    "scenario_name": eval_meta.get("scenario_name"),
                }
            },
        )
    except Exception as e:
        logger.warning(f"voice finalize annotation write failed: {e}")

    return VoiceSessionFinalizeResponse(
        **scored,
        scenario_name=eval_meta.get("scenario_name"),
        signaling_path=f"/api/v1/ws/signaling/{run.workflow_id}/{run.id}",
    )

