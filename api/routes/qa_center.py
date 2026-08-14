"""QA Center + Compliance API — org-scoped review queue, overrides, re-run (P4)."""

from __future__ import annotations

from datetime import datetime, time
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from api.db import db_client
from api.db.models import UserModel
from api.schemas.qa_center import (
    QaCenterDetailResponse,
    QaCenterQueueResponse,
    QaCenterSummary,
    QaManualOverridePayload,
    QaRerunResponse,
)
from api.services.auth.depends import get_user
from api.services.qa_center.enrich import (
    DEFAULT_MAX_SCORE,
    DEFAULT_PROBLEM_TAGS,
    build_qa_center_row,
    summarize_qa_center,
)
from api.services.qa_center.override import apply_manual_override, read_audit_history
from api.tasks.function_names import FunctionNames

router = APIRouter(prefix="/qa-center", tags=["qa-center"])


def _require_org(user: UserModel) -> int:
    if not user.selected_organization_id:
        raise HTTPException(status_code=400, detail="No organization selected")
    return int(user.selected_organization_id)


def _parse_range(from_date: str, to_date: str, timezone: str):
    try:
        tz = ZoneInfo(timezone)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid timezone: {timezone}") from exc
    try:
        start = datetime.combine(
            datetime.strptime(from_date, "%Y-%m-%d").date(), time.min, tzinfo=tz
        )
        end = datetime.combine(
            datetime.strptime(to_date, "%Y-%m-%d").date(), time.max, tzinfo=tz
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="from_date/to_date must be YYYY-MM-DD"
        ) from exc
    if end < start:
        raise HTTPException(status_code=400, detail="to_date must be >= from_date")
    return start.astimezone(ZoneInfo("UTC")), end.astimezone(ZoneInfo("UTC"))


def _parse_problem_tags(raw: Optional[str]) -> list[str]:
    if not raw or not raw.strip():
        return list(DEFAULT_PROBLEM_TAGS)
    return [t.strip() for t in raw.split(",") if t.strip()]


def _row_from_db(
    r: dict,
    *,
    max_score: float,
    problem_tags: list[str],
):
    gathered = r.get("gathered_context") or {}
    usage = r.get("usage_info") or {}
    initial = r.get("initial_context") or {}
    duration = usage.get("call_duration_seconds")
    try:
        duration_f = float(duration) if duration is not None else None
    except (TypeError, ValueError):
        duration_f = None
    return build_qa_center_row(
        run_id=int(r["id"]),
        workflow_id=int(r["workflow_id"]),
        workflow_name=r.get("workflow_name") or "",
        created_at=r.get("created_at"),
        is_completed=bool(r.get("is_completed")),
        disposition=gathered.get("mapped_call_disposition") or "UNKNOWN",
        phone_number=str(initial.get("phone_number") or ""),
        duration_seconds=duration_f,
        annotations=r.get("annotations"),
        max_score=max_score,
        problem_tags=problem_tags,
    )


@router.get("/health")
async def qa_center_health():
    return {
        "status": "ok",
        "module": "qa-center",
        "schema_version": 1,
        "default_max_score": DEFAULT_MAX_SCORE,
        "default_problem_tags": DEFAULT_PROBLEM_TAGS,
    }


@router.get("/summary", response_model=QaCenterSummary)
async def qa_center_summary(
    from_date: str = Query(..., description="YYYY-MM-DD"),
    to_date: str = Query(..., description="YYYY-MM-DD"),
    timezone: str = Query("UTC"),
    workflow_id: Optional[int] = Query(None),
    max_score: float = Query(DEFAULT_MAX_SCORE, ge=0, le=100),
    problem_tags: Optional[str] = Query(
        None, description="Comma-separated problem tags (default: built-in set)"
    ),
    user: UserModel = Depends(get_user),
) -> QaCenterSummary:
    org_id = _require_org(user)
    start_utc, end_utc = _parse_range(from_date, to_date, timezone)
    tags = _parse_problem_tags(problem_tags)
    raw_rows = await db_client.list_runs_for_summary(
        organization_id=org_id,
        start_utc=start_utc,
        end_utc=end_utc,
        workflow_id=workflow_id,
        max_rows=5000,
    )
    rows = [_row_from_db(r, max_score=max_score, problem_tags=tags) for r in raw_rows]
    summary = summarize_qa_center(rows, max_score=max_score, problem_tags=tags)
    return QaCenterSummary(
        from_date=from_date,
        to_date=to_date,
        timezone=timezone,
        workflow_id=workflow_id,
        **summary,
    )


@router.get("/queue", response_model=QaCenterQueueResponse)
async def qa_center_queue(
    from_date: str = Query(...),
    to_date: str = Query(...),
    timezone: str = Query("UTC"),
    workflow_id: Optional[int] = Query(None),
    max_score: float = Query(DEFAULT_MAX_SCORE, ge=0, le=100),
    problem_tags: Optional[str] = Query(None),
    only_needs_review: bool = Query(True),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user: UserModel = Depends(get_user),
) -> QaCenterQueueResponse:
    """Review queue: low score, problem tags, compliance fails, QA errors."""
    org_id = _require_org(user)
    start_utc, end_utc = _parse_range(from_date, to_date, timezone)
    tags = _parse_problem_tags(problem_tags)
    raw_rows = await db_client.list_runs_for_summary(
        organization_id=org_id,
        start_utc=start_utc,
        end_utc=end_utc,
        workflow_id=workflow_id,
        max_rows=5000,
    )
    rows = [_row_from_db(r, max_score=max_score, problem_tags=tags) for r in raw_rows]
    if only_needs_review:
        rows = [r for r in rows if r.needs_review]
    # Sort: compliance fails first, then low score, then newest
    rows.sort(
        key=lambda r: (
            -(r.compliance_fail_count),
            r.effective_score if r.effective_score is not None else 999,
            r.created_at or datetime.min,
        ),
    )
    total = len(rows)
    offset = max(0, (page - 1) * limit)
    page_rows = rows[offset : offset + limit]
    return QaCenterQueueResponse(
        total=total,
        page=page,
        limit=limit,
        max_score_threshold=max_score,
        problem_tags=tags,
        runs=page_rows,
    )


@router.get("/runs/{run_id}", response_model=QaCenterDetailResponse)
async def qa_center_run_detail(
    run_id: int,
    max_score: float = Query(DEFAULT_MAX_SCORE, ge=0, le=100),
    problem_tags: Optional[str] = Query(None),
    user: UserModel = Depends(get_user),
) -> QaCenterDetailResponse:
    org_id = _require_org(user)
    run = await db_client.get_workflow_run(run_id, organization_id=org_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    tags = _parse_problem_tags(problem_tags)
    workflow_name = ""
    try:
        workflow_name = await db_client.get_workflow_name(
            run.workflow_id, organization_id=org_id
        ) or ""
    except Exception:
        workflow_name = ""
    gathered = run.gathered_context or {}
    usage = run.usage_info or {}
    initial = run.initial_context or {}
    duration = usage.get("call_duration_seconds")
    try:
        duration_f = float(duration) if duration is not None else None
    except (TypeError, ValueError):
        duration_f = None
    row = build_qa_center_row(
        run_id=run.id,
        workflow_id=run.workflow_id,
        workflow_name=workflow_name,
        created_at=run.created_at,
        is_completed=bool(run.is_completed),
        disposition=gathered.get("mapped_call_disposition") or "UNKNOWN",
        phone_number=str(initial.get("phone_number") or ""),
        duration_seconds=duration_f,
        annotations=run.annotations,
        max_score=max_score,
        problem_tags=tags,
    )
    return QaCenterDetailResponse(
        run=row,
        audit_history=read_audit_history(run.annotations),
    )


@router.put("/runs/{run_id}/override", response_model=QaCenterDetailResponse)
async def qa_center_override(
    run_id: int,
    body: QaManualOverridePayload,
    user: UserModel = Depends(get_user),
) -> QaCenterDetailResponse:
    """Save manual QA override (reviewer correction) with audit history."""
    org_id = _require_org(user)
    run = await db_client.get_workflow_run(run_id, organization_id=org_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Workflow run not found")

    patch = apply_manual_override(
        run.annotations,
        body,
        reviewer_user_id=int(user.id),
        reviewer_email=getattr(user, "email", None),
    )
    await db_client.update_workflow_run(run_id, annotations=patch)
    # re-fetch
    run = await db_client.get_workflow_run(run_id, organization_id=org_id)
    assert run is not None
    gathered = run.gathered_context or {}
    usage = run.usage_info or {}
    initial = run.initial_context or {}
    duration = usage.get("call_duration_seconds")
    try:
        duration_f = float(duration) if duration is not None else None
    except (TypeError, ValueError):
        duration_f = None
    workflow_name = ""
    try:
        workflow_name = await db_client.get_workflow_name(
            run.workflow_id, organization_id=org_id
        ) or ""
    except Exception:
        pass
    row = build_qa_center_row(
        run_id=run.id,
        workflow_id=run.workflow_id,
        workflow_name=workflow_name,
        created_at=run.created_at,
        is_completed=bool(run.is_completed),
        disposition=gathered.get("mapped_call_disposition") or "UNKNOWN",
        phone_number=str(initial.get("phone_number") or ""),
        duration_seconds=duration_f,
        annotations=run.annotations,
    )
    return QaCenterDetailResponse(
        run=row,
        audit_history=read_audit_history(run.annotations),
    )


@router.post("/runs/{run_id}/rerun", response_model=QaRerunResponse)
async def qa_center_rerun(
    run_id: int,
    user: UserModel = Depends(get_user),
) -> QaRerunResponse:
    """Re-enqueue post-call integrations (includes QA nodes) via ARQ.

    Manual overrides under ``qa_manual_override`` are preserved (merge key).
    Requires a running ARQ worker; returns ``unavailable`` if enqueue fails.
    """
    org_id = _require_org(user)
    run = await db_client.get_workflow_run(run_id, organization_id=org_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    if not run.is_completed:
        raise HTTPException(
            status_code=400, detail="Run is not completed — QA re-run only after completion"
        )
    try:
        from api.tasks.arq import enqueue_job

        await enqueue_job(
            FunctionNames.RUN_INTEGRATIONS_POST_WORKFLOW_RUN,
            run_id,
        )
        return QaRerunResponse(
            run_id=run_id,
            status="queued",
            message="Post-call integrations (QA) enqueued",
        )
    except Exception as exc:
        logger.warning(f"QA re-run enqueue failed for run {run_id}: {exc}")
        return QaRerunResponse(
            run_id=run_id,
            status="unavailable",
            message=f"Could not enqueue ARQ job: {exc}",
        )
