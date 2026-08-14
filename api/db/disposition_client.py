"""Disposition taxonomy persistence on workflows.call_disposition_codes."""

from __future__ import annotations

from typing import Any

from sqlalchemy.future import select

from api.db.base_client import BaseDBClient
from api.db.models import WorkflowModel
from api.schemas.disposition_taxonomy import (
    DispositionTaxonomy,
    DispositionTaxonomyUpdate,
    OrgDispositionSummaryItem,
)
from api.services.disposition_taxonomy.service import (
    normalize_taxonomy,
    taxonomy_to_storage,
)


class DispositionClient(BaseDBClient):
    async def get_workflow_taxonomy(
        self, workflow_id: int, organization_id: int
    ) -> tuple[WorkflowModel, DispositionTaxonomy] | None:
        async with self.async_session() as session:
            result = await session.execute(
                select(WorkflowModel).where(
                    WorkflowModel.id == workflow_id,
                    WorkflowModel.organization_id == organization_id,
                )
            )
            workflow = result.scalar_one_or_none()
            if workflow is None:
                return None
            tax = normalize_taxonomy(workflow.call_disposition_codes)
            return workflow, tax

    async def set_workflow_taxonomy(
        self,
        workflow_id: int,
        organization_id: int,
        update: DispositionTaxonomyUpdate,
    ) -> tuple[WorkflowModel, DispositionTaxonomy] | None:
        async with self.async_session() as session:
            result = await session.execute(
                select(WorkflowModel).where(
                    WorkflowModel.id == workflow_id,
                    WorkflowModel.organization_id == organization_id,
                )
            )
            workflow = result.scalar_one_or_none()
            if workflow is None:
                return None

            tax = normalize_taxonomy(
                {
                    "disposition_codes": update.disposition_codes,
                    "success_codes": update.success_codes,
                    "code_meta": {
                        k: (v.model_dump() if hasattr(v, "model_dump") else v)
                        for k, v in (update.code_meta or {}).items()
                    },
                }
            )
            workflow.call_disposition_codes = taxonomy_to_storage(tax)
            await session.commit()
            await session.refresh(workflow)
            return workflow, tax

    async def list_org_disposition_summary(
        self, organization_id: int
    ) -> list[OrgDispositionSummaryItem]:
        async with self.async_session() as session:
            result = await session.execute(
                select(WorkflowModel).where(
                    WorkflowModel.organization_id == organization_id
                )
            )
            workflows = result.scalars().all()

        # aggregate by code
        by_code: dict[str, dict[str, Any]] = {}
        for wf in workflows:
            tax = normalize_taxonomy(wf.call_disposition_codes)
            success = set(tax.success_codes)
            for code in tax.disposition_codes:
                meta = tax.code_meta.get(code)
                entry = by_code.setdefault(
                    code,
                    {
                        "code": code,
                        "label": (meta.label if meta else code) or code,
                        "category": (meta.category if meta else "other") or "other",
                        "workflow_count": 0,
                        "is_success": code in success,
                    },
                )
                entry["workflow_count"] += 1
                if code in success:
                    entry["is_success"] = True
                if meta and meta.label:
                    entry["label"] = meta.label
                if meta and meta.category:
                    entry["category"] = meta.category

        items = [
            OrgDispositionSummaryItem(**v)
            for v in sorted(by_code.values(), key=lambda x: x["code"])
        ]
        return items
