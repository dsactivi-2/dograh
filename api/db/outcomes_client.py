"""DB access for Outcomes dashboard (org-scoped workflow runs)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import func, select

from api.db.base_client import BaseDBClient
from api.db.models import WorkflowModel, WorkflowRunModel


class OutcomesClient(BaseDBClient):
    async def list_runs_for_outcomes(
        self,
        organization_id: int,
        start_utc: datetime,
        end_utc: datetime,
        workflow_id: Optional[int] = None,
        page: int = 1,
        limit: int = 50,
    ) -> tuple[list[WorkflowRunModel], int]:
        """Return workflow runs in range with total count (org-scoped)."""
        async with self.async_session() as session:
            filters = [
                WorkflowModel.organization_id == organization_id,
                WorkflowRunModel.created_at >= start_utc,
                WorkflowRunModel.created_at <= end_utc,
            ]
            if workflow_id is not None:
                filters.append(WorkflowRunModel.workflow_id == workflow_id)

            count_q = (
                select(func.count(WorkflowRunModel.id))
                .select_from(WorkflowRunModel)
                .join(WorkflowModel, WorkflowRunModel.workflow_id == WorkflowModel.id)
                .where(*filters)
            )
            total = int((await session.execute(count_q)).scalar_one())

            offset = max(0, (page - 1) * limit)
            q = (
                select(WorkflowRunModel)
                .join(WorkflowModel, WorkflowRunModel.workflow_id == WorkflowModel.id)
                .where(*filters)
                .order_by(WorkflowRunModel.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            result = await session.execute(q)
            runs = list(result.scalars().all())
            return runs, total

    async def list_runs_for_summary(
        self,
        organization_id: int,
        start_utc: datetime,
        end_utc: datetime,
        workflow_id: Optional[int] = None,
        max_rows: int = 5000,
    ) -> list[dict[str, Any]]:
        """Lightweight rows for aggregation (disposition + annotations)."""
        async with self.async_session() as session:
            filters = [
                WorkflowModel.organization_id == organization_id,
                WorkflowRunModel.created_at >= start_utc,
                WorkflowRunModel.created_at <= end_utc,
            ]
            if workflow_id is not None:
                filters.append(WorkflowRunModel.workflow_id == workflow_id)

            q = (
                select(
                    WorkflowRunModel.id,
                    WorkflowRunModel.workflow_id,
                    WorkflowRunModel.is_completed,
                    WorkflowRunModel.gathered_context,
                    WorkflowRunModel.annotations,
                    WorkflowRunModel.usage_info,
                    WorkflowRunModel.initial_context,
                    WorkflowRunModel.created_at,
                    WorkflowModel.name.label("workflow_name"),
                )
                .join(WorkflowModel, WorkflowRunModel.workflow_id == WorkflowModel.id)
                .where(*filters)
                .order_by(WorkflowRunModel.created_at.desc())
                .limit(max_rows)
            )
            result = await session.execute(q)
            rows = []
            for row in result.all():
                rows.append(
                    {
                        "id": row.id,
                        "workflow_id": row.workflow_id,
                        "workflow_name": row.workflow_name or "",
                        "is_completed": bool(row.is_completed),
                        "gathered_context": row.gathered_context or {},
                        "annotations": row.annotations or {},
                        "usage_info": row.usage_info or {},
                        "initial_context": row.initial_context or {},
                        "created_at": row.created_at,
                    }
                )
            return rows
