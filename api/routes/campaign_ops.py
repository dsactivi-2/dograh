"""Campaign Control Tower API — funnel, retry, circuit-breaker visibility (P3)."""

from __future__ import annotations

from datetime import datetime, time
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from api.db import db_client
from api.db.models import UserModel
from api.schemas.campaign_ops import (
    CampaignOpsRow,
    CampaignOpsSummary,
    CircuitBreakerVisibility,
    DispositionBucket,
    FunnelStage,
    RetryVisibility,
)
from api.services.auth.depends import get_user
from api.services.campaign_ops.aggregate import (
    build_disposition_distribution,
    build_funnel_stages,
    count_connected_runs,
    parse_circuit_breaker_config,
    parse_retry_config,
)

router = APIRouter(prefix="/campaign-ops", tags=["campaign-ops"])


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


async def _live_circuit_breaker(
    campaign_id: int, cb_config: dict
) -> CircuitBreakerVisibility:
    base = CircuitBreakerVisibility(
        enabled=bool(cb_config.get("enabled", False)),
        failure_threshold=float(cb_config.get("failure_threshold", 0.5)),
        window_seconds=int(cb_config.get("window_seconds", 120)),
        min_calls_in_window=int(cb_config.get("min_calls_in_window", 5)),
        source="config",
    )
    if not base.enabled:
        return base
    try:
        from api.services.campaign.circuit_breaker import circuit_breaker

        is_open, stats = await circuit_breaker.is_circuit_open(
            campaign_id, config=cb_config
        )
        if stats is None:
            base.source = "unavailable"
            return base
        base.is_open = bool(is_open)
        base.failure_count = int(stats.get("failure_count") or 0)
        base.success_count = int(stats.get("success_count") or 0)
        base.failure_rate = float(stats.get("failure_rate") or 0.0)
        base.source = "redis"
        return base
    except Exception as exc:
        logger.debug(f"Circuit breaker live stats unavailable for {campaign_id}: {exc}")
        base.source = "unavailable"
        return base


@router.get("/health")
async def campaign_ops_health():
    return {"status": "ok", "module": "campaign-ops", "phase": "P3"}


@router.get("/summary", response_model=CampaignOpsSummary)
async def campaign_ops_summary(
    from_date: str = Query(..., description="YYYY-MM-DD"),
    to_date: str = Query(..., description="YYYY-MM-DD"),
    timezone: str = Query("UTC"),
    campaign_id: Optional[int] = Query(None),
    workflow_id: Optional[int] = Query(None),
    user: UserModel = Depends(get_user),
) -> CampaignOpsSummary:
    org_id = _require_org(user)
    start_utc, end_utc = _parse_range(from_date, to_date, timezone)

    campaigns = await db_client.list_campaigns_for_ops(
        organization_id=org_id,
        start_utc=start_utc,
        end_utc=end_utc,
        campaign_id=campaign_id,
        workflow_id=workflow_id,
    )
    campaign_ids = [int(c["id"]) for c in campaigns]

    queued_map = await db_client.queued_run_state_counts(campaign_ids)
    retry_map = await db_client.queued_run_retry_stats(campaign_ids)
    run_stats = await db_client.campaign_run_stats(
        organization_id=org_id,
        campaign_ids=campaign_ids,
        start_utc=start_utc,
        end_utc=end_utc,
    )

    rows: list[CampaignOpsRow] = []
    all_dispositions: list[str] = []
    agg_queued = {"queued": 0, "processing": 0, "processed": 0, "failed": 0, "total": 0}
    total_runs = 0
    total_connected = 0
    total_completed = 0

    for c in campaigns:
        cid = int(c["id"])
        qstats = queued_map.get(cid) or {
            "queued": 0,
            "processing": 0,
            "processed": 0,
            "failed": 0,
            "total": 0,
        }
        for k in ("queued", "processing", "processed", "failed", "total"):
            agg_queued[k] += int(qstats.get(k) or 0)

        rstat = run_stats.get(cid) or {
            "runs_total": 0,
            "runs_completed": 0,
            "run_rows": [],
        }
        run_rows = rstat.get("run_rows") or []
        connected = count_connected_runs(run_rows)
        dispositions = [rr.get("disposition") for rr in run_rows]
        all_dispositions.extend([str(d or "UNKNOWN") for d in dispositions])
        dist = build_disposition_distribution(dispositions)

        total_runs += int(rstat.get("runs_total") or 0)
        total_completed += int(rstat.get("runs_completed") or 0)
        total_connected += connected

        retry_cfg = parse_retry_config(c.get("retry_config"))
        retry_stats = retry_map.get(cid) or {}
        retry = RetryVisibility(
            enabled=retry_cfg["enabled"],
            max_retries=retry_cfg["max_retries"],
            retry_delay_seconds=retry_cfg["retry_delay_seconds"],
            total_with_retry=int(retry_stats.get("total_with_retry") or 0),
            max_observed_retry_count=int(
                retry_stats.get("max_observed_retry_count") or 0
            ),
            by_reason=dict(retry_stats.get("by_reason") or {}),
        )

        cb_cfg = parse_circuit_breaker_config(c.get("orchestrator_metadata") or {})
        cb = await _live_circuit_breaker(cid, cb_cfg)

        logs = c.get("logs") or []
        if isinstance(logs, list):
            recent_logs = [e for e in logs[-10:] if isinstance(e, dict)]
        else:
            recent_logs = []

        rows.append(
            CampaignOpsRow(
                campaign_id=cid,
                campaign_name=c.get("name") or "",
                workflow_id=int(c["workflow_id"]),
                workflow_name=c.get("workflow_name") or "",
                state=str(c.get("state") or ""),
                created_at=c.get("created_at"),
                started_at=c.get("started_at"),
                completed_at=c.get("completed_at"),
                total_rows=c.get("total_rows"),
                processed_rows=int(c.get("processed_rows") or 0),
                failed_rows=int(c.get("failed_rows") or 0),
                queued=int(qstats.get("queued") or 0),
                processing=int(qstats.get("processing") or 0),
                processed=int(qstats.get("processed") or 0),
                failed_queued=int(qstats.get("failed") or 0),
                total_queued_runs=int(qstats.get("total") or 0),
                runs_total=int(rstat.get("runs_total") or 0),
                runs_completed=int(rstat.get("runs_completed") or 0),
                runs_connected=connected,
                disposition_distribution=[
                    DispositionBucket(**d) for d in dist
                ],
                retry=retry,
                circuit_breaker=cb,
                recent_logs=recent_logs,
            )
        )

    dispositioned = sum(
        1
        for d in all_dispositions
        if d and str(d).upper() not in {"UNKNOWN", ""}
    )
    funnel = [
        FunnelStage(**s)
        for s in build_funnel_stages(
            agg_queued,
            runs_total=total_runs,
            runs_connected=total_connected,
            disposition_total=dispositioned,
        )
    ]
    org_dist = [
        DispositionBucket(**d) for d in build_disposition_distribution(all_dispositions)
    ]

    return CampaignOpsSummary(
        from_date=from_date,
        to_date=to_date,
        timezone=timezone,
        campaign_id=campaign_id,
        workflow_id=workflow_id,
        campaign_count=len(rows),
        funnel=funnel,
        disposition_distribution=org_dist,
        totals={
            "queued_runs": int(agg_queued.get("total") or 0),
            "queued": int(agg_queued.get("queued") or 0),
            "processing": int(agg_queued.get("processing") or 0),
            "processed": int(agg_queued.get("processed") or 0),
            "failed_queued": int(agg_queued.get("failed") or 0),
            "runs_total": total_runs,
            "runs_completed": total_completed,
            "runs_connected": total_connected,
            "dispositioned": dispositioned,
        },
        campaigns=rows,
    )


@router.get("/campaigns/{campaign_id}", response_model=CampaignOpsRow)
async def campaign_ops_detail(
    campaign_id: int,
    from_date: str = Query(...),
    to_date: str = Query(...),
    timezone: str = Query("UTC"),
    user: UserModel = Depends(get_user),
) -> CampaignOpsRow:
    summary = await campaign_ops_summary(
        from_date=from_date,
        to_date=to_date,
        timezone=timezone,
        campaign_id=campaign_id,
        workflow_id=None,
        user=user,
    )
    if not summary.campaigns:
        raise HTTPException(status_code=404, detail="Campaign not found in range")
    return summary.campaigns[0]
