"""DB access for Campaign Control Tower (org-scoped)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import func, or_, select

from api.db.base_client import BaseDBClient
from api.db.models import CampaignModel, QueuedRunModel, WorkflowModel, WorkflowRunModel


class CampaignOpsClient(BaseDBClient):
    async def list_campaigns_for_ops(
        self,
        organization_id: int,
        start_utc: Optional[datetime] = None,
        end_utc: Optional[datetime] = None,
        campaign_id: Optional[int] = None,
        workflow_id: Optional[int] = None,
        max_rows: int = 200,
    ) -> list[dict[str, Any]]:
        """Campaigns in org, optionally filtered by activity window / ids."""
        async with self.async_session() as session:
            filters = [CampaignModel.organization_id == organization_id]
            if campaign_id is not None:
                filters.append(CampaignModel.id == campaign_id)
            if workflow_id is not None:
                filters.append(CampaignModel.workflow_id == workflow_id)
            # Campaigns created or active within the selected range
            if start_utc is not None and end_utc is not None:
                filters.append(
                    or_(
                        CampaignModel.created_at.between(start_utc, end_utc),
                        CampaignModel.started_at.between(start_utc, end_utc),
                        CampaignModel.completed_at.between(start_utc, end_utc),
                        # Still-running campaigns started before the window
                        (
                            (CampaignModel.state.in_(["running", "paused", "syncing"]))
                            & (
                                (CampaignModel.started_at.is_(None))
                                | (CampaignModel.started_at <= end_utc)
                            )
                        ),
                    )
                )
            elif start_utc is not None:
                filters.append(
                    or_(
                        CampaignModel.created_at >= start_utc,
                        CampaignModel.started_at >= start_utc,
                        CampaignModel.completed_at >= start_utc,
                    )
                )
            elif end_utc is not None:
                filters.append(CampaignModel.created_at <= end_utc)

            q = (
                select(
                    CampaignModel.id,
                    CampaignModel.name,
                    CampaignModel.workflow_id,
                    CampaignModel.state,
                    CampaignModel.created_at,
                    CampaignModel.started_at,
                    CampaignModel.completed_at,
                    CampaignModel.total_rows,
                    CampaignModel.processed_rows,
                    CampaignModel.failed_rows,
                    CampaignModel.retry_config,
                    CampaignModel.orchestrator_metadata,
                    CampaignModel.logs,
                    WorkflowModel.name.label("workflow_name"),
                )
                .join(WorkflowModel, CampaignModel.workflow_id == WorkflowModel.id)
                .where(*filters)
                .order_by(CampaignModel.created_at.desc())
                .limit(max_rows)
            )
            result = await session.execute(q)
            rows = []
            for r in result.all():
                rows.append(
                    {
                        "id": r.id,
                        "name": r.name or "",
                        "workflow_id": r.workflow_id,
                        "workflow_name": r.workflow_name or "",
                        "state": r.state,
                        "created_at": r.created_at,
                        "started_at": r.started_at,
                        "completed_at": r.completed_at,
                        "total_rows": r.total_rows,
                        "processed_rows": int(r.processed_rows or 0),
                        "failed_rows": int(r.failed_rows or 0),
                        "retry_config": r.retry_config or {},
                        "orchestrator_metadata": r.orchestrator_metadata or {},
                        "logs": r.logs or [],
                    }
                )
            return rows

    async def queued_run_state_counts(
        self,
        campaign_ids: list[int],
    ) -> dict[int, dict[str, int]]:
        """Per-campaign counts of queued_runs by state."""
        if not campaign_ids:
            return {}
        async with self.async_session() as session:
            q = (
                select(
                    QueuedRunModel.campaign_id,
                    QueuedRunModel.state,
                    func.count(QueuedRunModel.id),
                )
                .where(QueuedRunModel.campaign_id.in_(campaign_ids))
                .group_by(QueuedRunModel.campaign_id, QueuedRunModel.state)
            )
            result = await session.execute(q)
            out: dict[int, dict[str, int]] = {
                cid: {
                    "queued": 0,
                    "processing": 0,
                    "processed": 0,
                    "failed": 0,
                    "total": 0,
                }
                for cid in campaign_ids
            }
            for cid, state, count in result.all():
                if cid not in out:
                    continue
                st = str(state or "")
                if st in out[cid]:
                    out[cid][st] += int(count)
                out[cid]["total"] += int(count)
            return out

    async def queued_run_retry_stats(
        self,
        campaign_ids: list[int],
    ) -> dict[int, dict[str, Any]]:
        """Retry visibility from queued_runs.retry_count / retry_reason."""
        if not campaign_ids:
            return {}
        async with self.async_session() as session:
            q = (
                select(
                    QueuedRunModel.campaign_id,
                    func.count(QueuedRunModel.id),
                    func.max(QueuedRunModel.retry_count),
                )
                .where(
                    QueuedRunModel.campaign_id.in_(campaign_ids),
                    QueuedRunModel.retry_count > 0,
                )
                .group_by(QueuedRunModel.campaign_id)
            )
            result = await session.execute(q)
            out: dict[int, dict[str, Any]] = {
                cid: {
                    "total_with_retry": 0,
                    "max_observed_retry_count": 0,
                    "by_reason": {},
                }
                for cid in campaign_ids
            }
            for cid, count, max_rc in result.all():
                if cid not in out:
                    continue
                out[cid]["total_with_retry"] = int(count or 0)
                out[cid]["max_observed_retry_count"] = int(max_rc or 0)

            rq = (
                select(
                    QueuedRunModel.campaign_id,
                    QueuedRunModel.retry_reason,
                    func.count(QueuedRunModel.id),
                )
                .where(
                    QueuedRunModel.campaign_id.in_(campaign_ids),
                    QueuedRunModel.retry_count > 0,
                    QueuedRunModel.retry_reason.isnot(None),
                )
                .group_by(QueuedRunModel.campaign_id, QueuedRunModel.retry_reason)
            )
            rresult = await session.execute(rq)
            for cid, reason, count in rresult.all():
                if cid not in out:
                    continue
                key = str(reason or "unknown")
                out[cid]["by_reason"][key] = int(count)
            return out

    async def campaign_run_stats(
        self,
        organization_id: int,
        campaign_ids: list[int],
        start_utc: Optional[datetime] = None,
        end_utc: Optional[datetime] = None,
    ) -> dict[int, dict[str, Any]]:
        """Workflow-run aggregates per campaign (counts + disposition samples)."""
        if not campaign_ids:
            return {}
        async with self.async_session() as session:
            filters = [
                WorkflowModel.organization_id == organization_id,
                WorkflowRunModel.campaign_id.in_(campaign_ids),
            ]
            if start_utc is not None:
                filters.append(WorkflowRunModel.created_at >= start_utc)
            if end_utc is not None:
                filters.append(WorkflowRunModel.created_at <= end_utc)

            q = (
                select(
                    WorkflowRunModel.campaign_id,
                    WorkflowRunModel.is_completed,
                    WorkflowRunModel.gathered_context,
                    WorkflowRunModel.usage_info,
                )
                .join(WorkflowModel, WorkflowRunModel.workflow_id == WorkflowModel.id)
                .where(*filters)
                .limit(10000)
            )
            result = await session.execute(q)
            out: dict[int, dict[str, Any]] = {
                cid: {
                    "runs_total": 0,
                    "runs_completed": 0,
                    "run_rows": [],
                }
                for cid in campaign_ids
            }
            for row in result.all():
                cid = row.campaign_id
                if cid not in out:
                    continue
                gathered = row.gathered_context or {}
                usage = row.usage_info or {}
                disposition = gathered.get("mapped_call_disposition") or "UNKNOWN"
                duration = usage.get("call_duration_seconds")
                try:
                    duration_f = float(duration) if duration is not None else None
                except (TypeError, ValueError):
                    duration_f = None
                is_completed = bool(row.is_completed)
                out[cid]["runs_total"] += 1
                if is_completed:
                    out[cid]["runs_completed"] += 1
                out[cid]["run_rows"].append(
                    {
                        "is_completed": is_completed,
                        "disposition": disposition,
                        "duration_seconds": duration_f,
                    }
                )
            return out
