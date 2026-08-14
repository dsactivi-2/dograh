"""DB access for Cost Attribution dashboard (org-scoped)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select

from api.db.base_client import BaseDBClient
from api.db.models import CampaignModel, WorkflowModel, WorkflowRunModel


class CostAttributionClient(BaseDBClient):
    async def list_runs_for_cost_attribution(
        self,
        organization_id: int,
        start_utc: datetime,
        end_utc: datetime,
        workflow_id: Optional[int] = None,
        campaign_id: Optional[int] = None,
        max_rows: int = 10000,
    ) -> list[dict[str, Any]]:
        """Lightweight run rows with cost_info / usage_info for aggregation."""
        async with self.async_session() as session:
            filters = [
                WorkflowModel.organization_id == organization_id,
                WorkflowRunModel.created_at >= start_utc,
                WorkflowRunModel.created_at <= end_utc,
            ]
            if workflow_id is not None:
                filters.append(WorkflowRunModel.workflow_id == workflow_id)
            if campaign_id is not None:
                filters.append(WorkflowRunModel.campaign_id == campaign_id)

            q = (
                select(
                    WorkflowRunModel.id,
                    WorkflowRunModel.workflow_id,
                    WorkflowRunModel.definition_id,
                    WorkflowRunModel.campaign_id,
                    WorkflowRunModel.cost_info,
                    WorkflowRunModel.usage_info,
                    WorkflowRunModel.is_completed,
                    WorkflowModel.name.label("workflow_name"),
                    CampaignModel.name.label("campaign_name"),
                )
                .join(WorkflowModel, WorkflowRunModel.workflow_id == WorkflowModel.id)
                .outerjoin(
                    CampaignModel, WorkflowRunModel.campaign_id == CampaignModel.id
                )
                .where(*filters)
                .order_by(WorkflowRunModel.created_at.desc())
                .limit(max_rows)
            )
            result = await session.execute(q)
            rows: list[dict[str, Any]] = []
            for r in result.all():
                did = r.definition_id
                rows.append(
                    {
                        "id": r.id,
                        "workflow_id": r.workflow_id,
                        "workflow_name": r.workflow_name or "",
                        "definition_id": did,
                        "definition_label": (
                            f"{r.workflow_name or 'Workflow'} · def {did}"
                            if did is not None
                            else "No definition"
                        ),
                        "campaign_id": r.campaign_id,
                        "campaign_name": r.campaign_name or (
                            f"Campaign {r.campaign_id}" if r.campaign_id else None
                        ),
                        "cost_info": r.cost_info or {},
                        "usage_info": r.usage_info or {},
                        "is_completed": bool(r.is_completed),
                    }
                )
            return rows
