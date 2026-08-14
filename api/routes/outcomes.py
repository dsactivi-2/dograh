"""Outcomes dashboard API — org-scoped disposition + normalized QA."""

from __future__ import annotations

from datetime import datetime, time
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query

from api.db import db_client
from api.db.models import UserModel
from api.schemas.outcomes import (
    OutcomeRunRow,
    OutcomesListResponse,
    OutcomesSummaryResponse,
    QaRunOutcome,
)
from api.services.auth.depends import get_user
from api.services.outcomes.normalize import normalize_run_qa, summarize_outcomes

router = APIRouter(prefix="/outcomes", tags=["outcomes"])


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
        start = datetime.combine(datetime.strptime(from_date, "%Y-%m-%d").date(), time.min, tzinfo=tz)
        end = datetime.combine(datetime.strptime(to_date, "%Y-%m-%d").date(), time.max, tzinfo=tz)
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="from_date/to_date must be YYYY-MM-DD"
        ) from exc
    if end < start:
        raise HTTPException(status_code=400, detail="to_date must be >= from_date")
    return start.astimezone(ZoneInfo("UTC")), end.astimezone(ZoneInfo("UTC"))


def _row_from_db(row: dict) -> dict:
    gathered = row.get("gathered_context") or {}
    usage = row.get("usage_info") or {}
    initial = row.get("initial_context") or {}
    qa = normalize_run_qa(
        run_id=int(row["id"]),
        annotations=row.get("annotations"),
        workflow_id=row.get("workflow_id"),
    )
    call_tags = gathered.get("call_tags") or []
    if not isinstance(call_tags, list):
        call_tags = [str(call_tags)] if call_tags else []
    duration = usage.get("call_duration_seconds")
    try:
        duration_f = float(duration) if duration is not None else None
    except (TypeError, ValueError):
        duration_f = None
    return {
        "run_id": int(row["id"]),
        "workflow_id": int(row["workflow_id"]),
        "workflow_name": row.get("workflow_name") or "",
        "created_at": row.get("created_at"),
        "is_completed": bool(row.get("is_completed")),
        "disposition": gathered.get("mapped_call_disposition") or "UNKNOWN",
        "phone_number": str(initial.get("phone_number") or ""),
        "duration_seconds": duration_f,
        "call_tags": [str(t) for t in call_tags],
        "qa": qa.model_dump(),
    }


@router.get("/health")
async def outcomes_health():
    return {"status": "ok", "module": "outcomes", "schema_version": 1}


@router.get("/summary", response_model=OutcomesSummaryResponse)
async def outcomes_summary(
    from_date: str = Query(..., description="YYYY-MM-DD"),
    to_date: str = Query(..., description="YYYY-MM-DD"),
    timezone: str = Query("UTC", description="IANA timezone"),
    workflow_id: Optional[int] = Query(None),
    user: UserModel = Depends(get_user),
) -> OutcomesSummaryResponse:
    org_id = _require_org(user)
    start_utc, end_utc = _parse_range(from_date, to_date, timezone)
    raw_rows = await db_client.list_runs_for_summary(
        organization_id=org_id,
        start_utc=start_utc,
        end_utc=end_utc,
        workflow_id=workflow_id,
    )
    normalized = [_row_from_db(r) for r in raw_rows]
    summary = summarize_outcomes(normalized)
    return OutcomesSummaryResponse(
        from_date=from_date,
        to_date=to_date,
        timezone=timezone,
        workflow_id=workflow_id,
        **summary,
    )


@router.get("/runs", response_model=OutcomesListResponse)
async def outcomes_runs(
    from_date: str = Query(...),
    to_date: str = Query(...),
    timezone: str = Query("UTC"),
    workflow_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user: UserModel = Depends(get_user),
) -> OutcomesListResponse:
    org_id = _require_org(user)
    start_utc, end_utc = _parse_range(from_date, to_date, timezone)
    # Use summary list + paginate in-memory for consistent shape; large orgs
    # should tighten date ranges (max_rows=5000 on summary path). For page
    # list we use the dedicated paged query.
    runs, total = await db_client.list_runs_for_outcomes(
        organization_id=org_id,
        start_utc=start_utc,
        end_utc=end_utc,
        workflow_id=workflow_id,
        page=page,
        limit=limit,
    )
    # Need workflow names — fetch lightly via summary path filter is heavy;
    # attach names from a small join already on model if loaded. We re-query
    # names via workflow_id map from list_runs_for_summary window when needed.
    name_rows = await db_client.list_runs_for_summary(
        organization_id=org_id,
        start_utc=start_utc,
        end_utc=end_utc,
        workflow_id=workflow_id,
        max_rows=5000,
    )
    name_by_id = {r["id"]: r.get("workflow_name") or "" for r in name_rows}

    out_rows: list[OutcomeRunRow] = []
    for run in runs:
        gathered = run.gathered_context or {}
        usage = run.usage_info or {}
        initial = run.initial_context or {}
        qa = normalize_run_qa(run.id, run.annotations, run.workflow_id)
        tags = gathered.get("call_tags") or []
        if not isinstance(tags, list):
            tags = [str(tags)] if tags else []
        duration = usage.get("call_duration_seconds")
        try:
            duration_f = float(duration) if duration is not None else None
        except (TypeError, ValueError):
            duration_f = None
        out_rows.append(
            OutcomeRunRow(
                run_id=run.id,
                workflow_id=run.workflow_id,
                workflow_name=name_by_id.get(run.id, ""),
                created_at=run.created_at,
                is_completed=bool(run.is_completed),
                disposition=gathered.get("mapped_call_disposition") or "UNKNOWN",
                phone_number=str(initial.get("phone_number") or ""),
                duration_seconds=duration_f,
                call_tags=[str(t) for t in tags],
                qa=qa,
            )
        )
    return OutcomesListResponse(total=total, page=page, limit=limit, runs=out_rows)


@router.get("/runs/{run_id}/qa", response_model=QaRunOutcome)
async def outcomes_run_qa(
    run_id: int,
    user: UserModel = Depends(get_user),
) -> QaRunOutcome:
    org_id = _require_org(user)
    run = await db_client.get_workflow_run(run_id, organization_id=org_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return normalize_run_qa(run.id, run.annotations, run.workflow_id)
