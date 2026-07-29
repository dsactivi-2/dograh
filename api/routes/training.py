"""Training / Schulung API — shadow quiz + text drills (P5)."""

from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from pipecat.utils.run_context import set_current_run_id

from api.db import db_client
from api.db.models import UserModel
from api.enums import WorkflowRunMode
from api.schemas.text_eval import EvalAssertion, EvalTurn, TextEvalScenario
from api.schemas.training import (
    ShadowCompleteRequest,
    TextDrillRunRequest,
    TrainingAttemptListResponse,
    TrainingAttemptResponse,
    TrainingModuleCreate,
    TrainingModuleListResponse,
    TrainingModuleResponse,
    TrainingModuleUpdate,
    TrainingProgressResponse,
    ModuleProgressItem,
    VoiceDrillCompleteRequest,
    VoiceDrillStartRequest,
    VoiceDrillStartResponse,
)
from api.services.auth.depends import get_user
from api.services.evals.text_harness import run_text_eval_scenario
from api.services.evals.voice_guards import (
    VoiceEvalGuardError,
    check_voice_eval_allowed,
    clamp_max_duration_seconds,
    http_status_for_guard,
    voice_eval_guard_payload,
)
from api.services.evals.voice_score import score_voice_run
from api.services.quota_service import authorize_workflow_run_start
from api.services.training.score import (
    score_shadow_quiz,
    score_text_drill,
    score_voice_drill,
    strip_quiz_answers,
)
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

router = APIRouter(prefix="/training", tags=["training"])


def _require_org(user: UserModel) -> int:
    if not user.selected_organization_id:
        raise HTTPException(status_code=400, detail="No organization selected")
    return int(user.selected_organization_id)


def _assistant_from_session(session_data: dict[str, Any]) -> str:
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


async def _workflow_name(workflow_id: Optional[int], org_id: int) -> str:
    if workflow_id is None:
        return ""
    try:
        return await db_client.get_workflow_name(workflow_id, organization_id=org_id) or ""
    except Exception:
        return ""


def _module_to_response(
    m,
    *,
    workflow_name: str = "",
    strip_answers: bool = True,
    stats: Optional[dict[str, Any]] = None,
) -> TrainingModuleResponse:
    content = m.content or {}
    if strip_answers and m.mode == "shadow":
        content = strip_quiz_answers(content)
    st = stats or {}
    return TrainingModuleResponse(
        id=m.id,
        organization_id=m.organization_id,
        title=m.title,
        description=m.description or "",
        mode=m.mode,
        workflow_id=m.workflow_id,
        workflow_name=workflow_name,
        script_entry_id=m.script_entry_id,
        success_codes=list(m.success_codes or []),
        tags=list(m.tags or []),
        difficulty=m.difficulty or "beginner",
        pass_score=float(m.pass_score or 70),
        content=content,
        is_published=bool(m.is_published),
        created_by_user_id=m.created_by_user_id,
        created_at=m.created_at,
        best_score=st.get("best_score"),
        attempts_count=int(st.get("attempts_count") or 0),
        completed=bool(st.get("completed")),
    )


@router.get("/health")
async def training_health():
    return {
        "status": "ok",
        "module": "training",
        "modes": ["shadow", "text", "voice"],
        "voice_pipeline_duration_cap": True,
        "schema_version": 1,
    }


@router.get("/modules", response_model=TrainingModuleListResponse)
async def list_modules(
    mode: Optional[str] = Query(None),
    published_only: bool = Query(True),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user: UserModel = Depends(get_user),
) -> TrainingModuleListResponse:
    org_id = _require_org(user)
    rows, total = await db_client.list_training_modules(
        org_id, mode=mode, published_only=published_only, page=page, limit=limit
    )
    stats = await db_client.get_user_module_stats(org_id, int(user.id))
    items = []
    for m in rows:
        wn = await _workflow_name(m.workflow_id, org_id)
        items.append(
            _module_to_response(
                m,
                workflow_name=wn,
                strip_answers=True,
                stats=stats.get(m.id),
            )
        )
    return TrainingModuleListResponse(total=total, items=items)


@router.post("/modules", response_model=TrainingModuleResponse)
async def create_module(
    body: TrainingModuleCreate,
    user: UserModel = Depends(get_user),
) -> TrainingModuleResponse:
    org_id = _require_org(user)
    if body.mode in ("text", "voice") and not body.workflow_id:
        raise HTTPException(
            status_code=400, detail=f"{body.mode} modules require workflow_id"
        )
    try:
        m = await db_client.create_training_module(
            organization_id=org_id,
            title=body.title,
            created_by_user_id=int(user.id),
            description=body.description,
            mode=body.mode,
            workflow_id=body.workflow_id,
            script_entry_id=body.script_entry_id,
            success_codes=body.success_codes,
            tags=body.tags,
            difficulty=body.difficulty,
            pass_score=body.pass_score,
            content=body.content,
            is_published=body.is_published,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    wn = await _workflow_name(m.workflow_id, org_id)
    # creators see full content including answers
    return _module_to_response(m, workflow_name=wn, strip_answers=False)


@router.get("/modules/{module_id}", response_model=TrainingModuleResponse)
async def get_module(
    module_id: int,
    include_answers: bool = Query(False),
    user: UserModel = Depends(get_user),
) -> TrainingModuleResponse:
    org_id = _require_org(user)
    m = await db_client.get_training_module(module_id, org_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Module not found")
    # only creator or superuser can see quiz answers
    is_owner = int(m.created_by_user_id) == int(user.id)
    is_super = bool(getattr(user, "is_superuser", False))
    strip = not (include_answers and (is_owner or is_super))
    stats = await db_client.get_user_module_stats(org_id, int(user.id))
    wn = await _workflow_name(m.workflow_id, org_id)
    return _module_to_response(
        m, workflow_name=wn, strip_answers=strip, stats=stats.get(m.id)
    )


@router.patch("/modules/{module_id}", response_model=TrainingModuleResponse)
async def update_module(
    module_id: int,
    body: TrainingModuleUpdate,
    user: UserModel = Depends(get_user),
) -> TrainingModuleResponse:
    org_id = _require_org(user)
    m = await db_client.get_training_module(module_id, org_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Module not found")
    is_owner = int(m.created_by_user_id) == int(user.id)
    is_super = bool(getattr(user, "is_superuser", False))
    if not (is_owner or is_super):
        raise HTTPException(status_code=403, detail="Only creator or superuser can edit")
    data = body.model_dump(exclude_unset=True)
    updated = await db_client.update_training_module(module_id, org_id, **data)
    assert updated is not None
    wn = await _workflow_name(updated.workflow_id, org_id)
    return _module_to_response(updated, workflow_name=wn, strip_answers=False)


@router.delete("/modules/{module_id}")
async def delete_module(
    module_id: int,
    user: UserModel = Depends(get_user),
):
    org_id = _require_org(user)
    m = await db_client.get_training_module(module_id, org_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Module not found")
    is_owner = int(m.created_by_user_id) == int(user.id)
    is_super = bool(getattr(user, "is_superuser", False))
    if not (is_owner or is_super):
        raise HTTPException(status_code=403, detail="Only creator or superuser can delete")
    await db_client.delete_training_module(module_id, org_id)
    return {"status": "deleted", "id": module_id}


@router.get("/progress", response_model=TrainingProgressResponse)
async def my_progress(user: UserModel = Depends(get_user)) -> TrainingProgressResponse:
    org_id = _require_org(user)
    modules, _ = await db_client.list_training_modules(
        org_id, published_only=True, page=1, limit=200
    )
    stats = await db_client.get_user_module_stats(org_id, int(user.id))
    items: list[ModuleProgressItem] = []
    completed = 0
    bests: list[float] = []
    attempts_total = 0
    for m in modules:
        st = stats.get(m.id) or {}
        if st.get("completed"):
            completed += 1
        if st.get("best_score") is not None:
            bests.append(float(st["best_score"]))
        attempts_total += int(st.get("attempts_count") or 0)
        items.append(
            ModuleProgressItem(
                module_id=m.id,
                title=m.title,
                mode=m.mode,
                difficulty=m.difficulty or "beginner",
                pass_score=float(m.pass_score or 70),
                attempts_count=int(st.get("attempts_count") or 0),
                best_score=st.get("best_score"),
                last_score=st.get("last_score"),
                completed=bool(st.get("completed")),
                last_attempt_at=st.get("last_attempt_at"),
            )
        )
    total = len(modules)
    return TrainingProgressResponse(
        organization_id=org_id,
        user_id=int(user.id),
        modules_total=total,
        modules_completed=completed,
        completion_pct=round((completed / total * 100) if total else 0, 2),
        average_best_score=(sum(bests) / len(bests)) if bests else None,
        attempts_total=attempts_total,
        modules=items,
    )


@router.get("/attempts", response_model=TrainingAttemptListResponse)
async def list_my_attempts(
    module_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user: UserModel = Depends(get_user),
) -> TrainingAttemptListResponse:
    org_id = _require_org(user)
    rows, total = await db_client.list_training_attempts(
        org_id, user_id=int(user.id), module_id=module_id, page=page, limit=limit
    )
    items = []
    for a in rows:
        m = await db_client.get_training_module(a.module_id, org_id)
        items.append(
            TrainingAttemptResponse(
                id=a.id,
                module_id=a.module_id,
                module_title=m.title if m else "",
                user_id=a.user_id,
                mode=a.mode,
                score=float(a.score),
                passed=bool(a.passed),
                result=a.result or {},
                workflow_run_id=a.workflow_run_id,
                created_at=a.created_at,
            )
        )
    return TrainingAttemptListResponse(total=total, items=items)


@router.post(
    "/modules/{module_id}/shadow/complete",
    response_model=TrainingAttemptResponse,
)
async def complete_shadow(
    module_id: int,
    body: ShadowCompleteRequest,
    user: UserModel = Depends(get_user),
) -> TrainingAttemptResponse:
    org_id = _require_org(user)
    m = await db_client.get_training_module(module_id, org_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Module not found")
    if m.mode != "shadow":
        raise HTTPException(status_code=400, detail="Module is not shadow mode")
    if not m.is_published and int(m.created_by_user_id) != int(user.id):
        raise HTTPException(status_code=403, detail="Module not published")

    scored = score_shadow_quiz(
        m.content,
        [a.model_dump() for a in body.answers],
        pass_score=float(m.pass_score or 70),
    )
    attempt = await db_client.create_training_attempt(
        organization_id=org_id,
        module_id=m.id,
        user_id=int(user.id),
        mode="shadow",
        score=float(scored["score"]),
        passed=bool(scored["passed"]),
        result=scored,
    )
    return TrainingAttemptResponse(
        id=attempt.id,
        module_id=m.id,
        module_title=m.title,
        user_id=int(user.id),
        mode="shadow",
        score=float(attempt.score),
        passed=bool(attempt.passed),
        result=attempt.result or {},
        workflow_run_id=None,
        created_at=attempt.created_at,
    )


@router.post(
    "/modules/{module_id}/text/run",
    response_model=TrainingAttemptResponse,
)
async def run_text_drill(
    module_id: int,
    body: TextDrillRunRequest | None = None,
    user: UserModel = Depends(get_user),
) -> TrainingAttemptResponse:
    """Run scripted text drill via the P2 text-eval harness; score vs success set."""
    org_id = _require_org(user)
    m = await db_client.get_training_module(module_id, org_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Module not found")
    if m.mode != "text":
        raise HTTPException(status_code=400, detail="Module is not text mode")
    if not m.workflow_id:
        raise HTTPException(status_code=400, detail="Module has no workflow_id")
    if not m.is_published and int(m.created_by_user_id) != int(user.id):
        raise HTTPException(status_code=403, detail="Module not published")

    content = m.content or {}
    turns_raw = content.get("turns") or []
    if not turns_raw:
        raise HTTPException(
            status_code=400, detail="Text module content.turns is empty"
        )

    initial = dict(content.get("initial_context") or {})
    if body and body.initial_context:
        initial.update(body.initial_context)

    turns: list[EvalTurn] = []
    for t in turns_raw:
        if not isinstance(t, dict) or not t.get("user"):
            continue
        assertions = []
        for a in t.get("assertions") or []:
            if isinstance(a, dict) and a.get("type"):
                assertions.append(EvalAssertion(**a))
        turns.append(EvalTurn(user=str(t["user"]), assertions=assertions))
    if not turns:
        raise HTTPException(status_code=400, detail="No valid turns in content")

    final_assertions = []
    for a in content.get("final_assertions") or []:
        if isinstance(a, dict) and a.get("type"):
            final_assertions.append(EvalAssertion(**a))

    scenario = TextEvalScenario(
        name=str(content.get("scenario_name") or f"training-{m.id}"),
        workflow_id=int(m.workflow_id),
        initial_context=initial,
        turns=turns,
        final_assertions=final_assertions,
    )

    workflow = await db_client.get_workflow(m.workflow_id, organization_id=org_id)
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
        name = f"TRAIN-{uuid4().hex[:8].upper()}"
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

        await db_client.update_workflow_run(
            workflow_run.id,
            annotations={
                "tester": {"source": "training_text_drill", "modality": "text"},
                "training": {"module_id": m.id, "module_title": m.title},
            },
        )
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
            logger.warning(f"training session init issue: {e}")
        return {"workflow_run_id": workflow_run.id}

    async def execute_turn(run_id: int, text: str):
        text_session = await db_client.get_workflow_run_text_session(
            run_id, organization_id=org_id
        )
        if not text_session:
            raise RuntimeError("text session missing")
        quota = await authorize_workflow_run_start(
            workflow_id=int(m.workflow_id),
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
            workflow_id=int(m.workflow_id),
            run_id=run_id,
            text_session=text_session,
        )
        run = await db_client.get_workflow_run(run_id, organization_id=org_id)
        gathered = (run.gathered_context if run else {}) or {}
        assistant = _assistant_from_session(text_session.session_data or {})
        return {"assistant_text": assistant, "gathered_context": gathered}

    eval_result = await run_text_eval_scenario(
        scenario=scenario,
        organization_id=org_id,
        user_id=user.id,
        execute_turn=execute_turn,
        create_session=create_session,
    )

    # flatten assertions for scoring
    flat_assertions: list[dict[str, Any]] = []
    for tr in eval_result.turns:
        for ar in tr.assertions:
            flat_assertions.append(ar.model_dump())
    for ar in eval_result.final_assertions:
        flat_assertions.append(ar.model_dump())

    disposition = (eval_result.gathered_context or {}).get("mapped_call_disposition")
    scored = score_text_drill(
        eval_passed=bool(eval_result.passed),
        assertion_results=flat_assertions,
        disposition=disposition if isinstance(disposition, str) else None,
        success_codes=list(m.success_codes or []),
        pass_score=float(m.pass_score or 70),
    )
    scored["eval"] = eval_result.model_dump()
    if eval_result.error:
        scored["error"] = eval_result.error

    attempt = await db_client.create_training_attempt(
        organization_id=org_id,
        module_id=m.id,
        user_id=int(user.id),
        mode="text",
        score=float(scored["score"]),
        passed=bool(scored["passed"]),
        result=scored,
        workflow_run_id=eval_result.workflow_run_id,
    )
    return TrainingAttemptResponse(
        id=attempt.id,
        module_id=m.id,
        module_title=m.title,
        user_id=int(user.id),
        mode="text",
        score=float(attempt.score),
        passed=bool(attempt.passed),
        result=attempt.result or {},
        workflow_run_id=attempt.workflow_run_id,
        created_at=attempt.created_at,
    )


@router.post(
    "/modules/{module_id}/voice/start",
    response_model=VoiceDrillStartResponse,
)
async def start_voice_drill(
    module_id: int,
    body: VoiceDrillStartRequest | None = None,
    user: UserModel = Depends(get_user),
) -> VoiceDrillStartResponse:
    """Create a short SMALLWEBRTC run for a voice training drill (human-in-the-loop)."""
    org_id = _require_org(user)
    body = body or VoiceDrillStartRequest()
    m = await db_client.get_training_module(module_id, org_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Module not found")
    if m.mode != "voice":
        raise HTTPException(status_code=400, detail="Module is not voice mode")
    if not m.workflow_id:
        raise HTTPException(status_code=400, detail="Module has no workflow_id")
    if not m.is_published and int(m.created_by_user_id) != int(user.id):
        raise HTTPException(status_code=403, detail="Module not published")

    recent = await db_client.count_recent_voice_eval_sessions(org_id, hours=1)
    try:
        guards = check_voice_eval_allowed(recent_session_count=recent, batch_size=1)
    except VoiceEvalGuardError as e:
        raise HTTPException(
            status_code=http_status_for_guard(e.code),
            detail={"code": e.code, "message": e.message},
        ) from e

    workflow = await db_client.get_workflow(m.workflow_id, organization_id=org_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    max_dur = clamp_max_duration_seconds(body.max_duration_seconds)
    content = m.content or {}
    initial = dict(content.get("initial_context") or {})
    if body.initial_context:
        initial.update(body.initial_context)

    run_inputs = await prepare_workflow_run_inputs(
        db_client,
        workflow,
        initial_context=initial,
        use_draft=True,
        include_template_context=True,
    )
    name = f"VTRAIN-{uuid4().hex[:8].upper()}"
    workflow_run = await db_client.create_workflow_run(
        name=name,
        workflow_id=int(m.workflow_id),
        mode=WorkflowRunMode.SMALLWEBRTC.value,
        user_id=user.id,
        initial_context=run_inputs.initial_context,
        organization_id=org_id,
        definition_id=run_inputs.definition_id,
    )
    set_current_run_id(workflow_run.id)

    quota = await authorize_workflow_run_start(
        workflow_id=int(m.workflow_id),
        organization_id=org_id,
        workflow_run_id=workflow_run.id,
        actor_user=user,
    )
    if not quota.has_quota:
        raise HTTPException(status_code=402, detail=quota.error_message)

    guard_meta = voice_eval_guard_payload(
        recent_session_count=recent,
        max_duration_seconds=max_dur,
        source="training_voice_drill",
    )
    await db_client.update_workflow_run(
        workflow_run.id,
        annotations={
            "tester": guard_meta,
            "training": {
                "module_id": m.id,
                "module_title": m.title,
                "mode": "voice",
                "success_codes": list(m.success_codes or []),
                "pass_score": float(m.pass_score or 70),
                "assertions": content.get("assertions") or [],
            },
        },
        initial_context={
            "training_voice": {
                "module_id": m.id,
                "max_duration_hint_seconds": max_dur,
            }
        },
    )

    return VoiceDrillStartResponse(
        module_id=m.id,
        workflow_id=int(m.workflow_id),
        workflow_run_id=workflow_run.id,
        max_duration_hint_seconds=max_dur,
        signaling_path=f"/api/v1/ws/signaling/{m.workflow_id}/{workflow_run.id}",
        guards=guards,
    )


@router.post(
    "/modules/{module_id}/voice/complete",
    response_model=TrainingAttemptResponse,
)
async def complete_voice_drill(
    module_id: int,
    body: VoiceDrillCompleteRequest,
    user: UserModel = Depends(get_user),
) -> TrainingAttemptResponse:
    """Score a completed voice training run and store the attempt."""
    org_id = _require_org(user)
    m = await db_client.get_training_module(module_id, org_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Module not found")
    if m.mode != "voice":
        raise HTTPException(status_code=400, detail="Module is not voice mode")
    if not m.is_published and int(m.created_by_user_id) != int(user.id):
        raise HTTPException(status_code=403, detail="Module not published")

    run = await db_client.get_workflow_run(
        body.workflow_run_id, organization_id=org_id
    )
    if not run:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    # Ensure run is tagged for this module (or at least same workflow)
    ann = run.annotations if isinstance(run.annotations, dict) else {}
    training_meta = ann.get("training") if isinstance(ann.get("training"), dict) else {}
    if training_meta.get("module_id") not in (None, m.id) and int(
        training_meta.get("module_id") or 0
    ) != int(m.id):
        raise HTTPException(
            status_code=400, detail="Run is not linked to this training module"
        )
    if m.workflow_id and run.workflow_id != m.workflow_id:
        raise HTTPException(
            status_code=400, detail="Run workflow does not match module workflow"
        )

    content = m.content or {}
    assertions = content.get("assertions") or []
    scored_raw = score_voice_run(
        run_id=run.id,
        workflow_id=run.workflow_id,
        mode=run.mode,
        is_completed=bool(run.is_completed),
        logs=run.logs,
        gathered_context=run.gathered_context,
        annotations=run.annotations,
        assertions=assertions,
        success_codes=list(m.success_codes or []),
        pass_score=float(m.pass_score or 70),
        include_qa=body.include_qa,
    )
    scored = score_voice_drill(
        voice_score_payload=scored_raw,
        pass_score=float(m.pass_score or 70),
    )
    scored["module_id"] = m.id

    attempt = await db_client.create_training_attempt(
        organization_id=org_id,
        module_id=m.id,
        user_id=int(user.id),
        mode="voice",
        score=float(scored["score"]),
        passed=bool(scored["passed"]),
        result=scored,
        workflow_run_id=run.id,
    )
    try:
        await db_client.update_workflow_run(
            run.id,
            annotations={
                "voice_eval": {
                    "score": scored["score"],
                    "passed": scored["passed"],
                    "source": "training.voice.complete",
                    "module_id": m.id,
                    "scored_by_user_id": int(user.id),
                }
            },
        )
    except Exception as e:
        logger.warning(f"training voice annotation write failed: {e}")

    return TrainingAttemptResponse(
        id=attempt.id,
        module_id=m.id,
        module_title=m.title,
        user_id=int(user.id),
        mode="voice",
        score=float(attempt.score),
        passed=bool(attempt.passed),
        result=attempt.result or {},
        workflow_run_id=attempt.workflow_run_id,
        created_at=attempt.created_at,
    )

