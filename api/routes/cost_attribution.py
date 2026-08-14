"""Cost Attribution API — aggregate cost_info/usage_info by workflow/campaign/definition (P3)."""

from __future__ import annotations

from datetime import datetime, time
from typing import Literal, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query

from api.db import db_client
from api.db.models import UserModel
from api.schemas.cost_attribution import CostAttributionSummary, CostBucket
from api.services.auth.depends import get_user
from api.services.cost_attribution.extract import summarize_cost_rows

router = APIRouter(prefix="/cost-attribution", tags=["cost-attribution"])


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


@router.get("/health")
async def cost_attribution_health():
    return {"status": "ok", "module": "cost-attribution", "phase": "P3"}


@router.get("/summary", response_model=CostAttributionSummary)
async def cost_attribution_summary(
    from_date: str = Query(..., description="YYYY-MM-DD"),
    to_date: str = Query(..., description="YYYY-MM-DD"),
    timezone: str = Query("UTC"),
    workflow_id: Optional[int] = Query(None),
    campaign_id: Optional[int] = Query(None),
    group_by: Literal["workflow", "campaign", "definition"] = Query("workflow"),
    user: UserModel = Depends(get_user),
) -> CostAttributionSummary:
    org_id = _require_org(user)
    start_utc, end_utc = _parse_range(from_date, to_date, timezone)

    rows = await db_client.list_runs_for_cost_attribution(
        organization_id=org_id,
        start_utc=start_utc,
        end_utc=end_utc,
        workflow_id=workflow_id,
        campaign_id=campaign_id,
    )
    summary = summarize_cost_rows(rows, group_by=group_by)
    return CostAttributionSummary(
        from_date=from_date,
        to_date=to_date,
        timezone=timezone,
        workflow_id=workflow_id,
        campaign_id=campaign_id,
        group_by=group_by,
        total_runs=summary["total_runs"],
        runs_with_cost=summary["runs_with_cost"],
        runs_missing_cost=summary["runs_missing_cost"],
        cost_coverage_pct=summary["cost_coverage_pct"],
        total_duration_seconds=summary["total_duration_seconds"],
        total_cost_usd=summary["total_cost_usd"],
        total_charge_usd=summary["total_charge_usd"],
        total_dograh_tokens=summary["total_dograh_tokens"],
        buckets=[CostBucket(**b) for b in summary["buckets"]],
        notes=list(summary.get("notes") or []),
    )
