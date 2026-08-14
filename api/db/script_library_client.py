"""Script library + prompt search (Postgres FTS) client."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Optional

from sqlalchemy import String, cast, func, or_
from sqlalchemy.future import select

from api.db.base_client import BaseDBClient
from api.db.models import (
    ScriptLibraryEntryModel,
    UserModel,
    WorkflowDefinitionModel,
    WorkflowModel,
)
from api.services.script_library.extract import extract_node_prompts


class ScriptLibraryClient(BaseDBClient):
    async def create_script_entry(
        self,
        *,
        organization_id: int,
        workflow_id: int,
        title: str,
        owner_user_id: int,
        description: str = "",
        tags: list[str] | None = None,
        definition_id: int | None = None,
    ) -> ScriptLibraryEntryModel:
        async with self.async_session() as session:
            wf = await session.execute(
                select(WorkflowModel).where(
                    WorkflowModel.id == workflow_id,
                    WorkflowModel.organization_id == organization_id,
                )
            )
            if wf.scalar_one_or_none() is None:
                raise ValueError("Workflow not found in organization")

            if definition_id is not None:
                def_row = await session.execute(
                    select(WorkflowDefinitionModel).where(
                        WorkflowDefinitionModel.id == definition_id,
                        WorkflowDefinitionModel.workflow_id == workflow_id,
                    )
                )
                if def_row.scalar_one_or_none() is None:
                    raise ValueError("Definition not found for workflow")

            entry = ScriptLibraryEntryModel(
                organization_id=organization_id,
                workflow_id=workflow_id,
                definition_id=definition_id,
                title=title.strip(),
                description=description or "",
                tags=list(tags or []),
                owner_user_id=owner_user_id,
                approval_status="draft",
            )
            session.add(entry)
            await session.commit()
            await session.refresh(entry)
            return entry

    async def get_script_entry(
        self, entry_id: int, organization_id: int
    ) -> ScriptLibraryEntryModel | None:
        async with self.async_session() as session:
            result = await session.execute(
                select(ScriptLibraryEntryModel).where(
                    ScriptLibraryEntryModel.id == entry_id,
                    ScriptLibraryEntryModel.organization_id == organization_id,
                )
            )
            return result.scalar_one_or_none()

    async def list_script_entries(
        self,
        organization_id: int,
        *,
        workflow_id: int | None = None,
        approval_status: str | None = None,
        tag: str | None = None,
        owner_user_id: int | None = None,
        page: int = 1,
        limit: int = 50,
    ) -> tuple[list[ScriptLibraryEntryModel], int]:
        async with self.async_session() as session:
            filters = [ScriptLibraryEntryModel.organization_id == organization_id]
            if workflow_id is not None:
                filters.append(ScriptLibraryEntryModel.workflow_id == workflow_id)
            if approval_status:
                filters.append(
                    ScriptLibraryEntryModel.approval_status == approval_status
                )
            if owner_user_id is not None:
                filters.append(ScriptLibraryEntryModel.owner_user_id == owner_user_id)

            count_q = select(func.count(ScriptLibraryEntryModel.id)).where(*filters)
            total = int((await session.execute(count_q)).scalar() or 0)

            q = (
                select(ScriptLibraryEntryModel)
                .where(*filters)
                .order_by(ScriptLibraryEntryModel.updated_at.desc().nullslast())
                .offset(max(page - 1, 0) * limit)
                .limit(limit)
            )
            rows = list((await session.execute(q)).scalars().all())

            if tag:
                tag_l = tag.strip().lower()
                rows = [
                    r
                    for r in rows
                    if any(str(t).lower() == tag_l for t in (r.tags or []))
                ]
            return rows, total

    async def update_script_entry(
        self,
        entry_id: int,
        organization_id: int,
        *,
        title: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        definition_id: int | None = None,
        approval_status: str | None = None,
        actor_user_id: int,
        actor_is_superuser: bool = False,
    ) -> ScriptLibraryEntryModel | None:
        async with self.async_session() as session:
            result = await session.execute(
                select(ScriptLibraryEntryModel).where(
                    ScriptLibraryEntryModel.id == entry_id,
                    ScriptLibraryEntryModel.organization_id == organization_id,
                )
            )
            entry = result.scalar_one_or_none()
            if entry is None:
                return None

            if title is not None:
                entry.title = title.strip()
            if description is not None:
                entry.description = description
            if tags is not None:
                entry.tags = list(tags)
            if definition_id is not None:
                entry.definition_id = definition_id

            if approval_status is not None and approval_status != entry.approval_status:
                can_approve = actor_is_superuser or entry.owner_user_id == actor_user_id
                if approval_status in ("approved", "rejected") and not can_approve:
                    raise PermissionError(
                        "Only owner or superuser can approve/reject scripts"
                    )
                entry.approval_status = approval_status
                if approval_status == "approved":
                    entry.approved_by_user_id = actor_user_id
                    entry.approved_at = datetime.now(UTC)
                elif approval_status == "rejected":
                    entry.approved_by_user_id = actor_user_id
                    entry.approved_at = datetime.now(UTC)
                elif approval_status in ("draft", "pending"):
                    entry.approved_by_user_id = None
                    entry.approved_at = None

            entry.updated_at = datetime.now(UTC)
            await session.commit()
            await session.refresh(entry)
            return entry

    async def delete_script_entry(
        self, entry_id: int, organization_id: int
    ) -> bool:
        async with self.async_session() as session:
            result = await session.execute(
                select(ScriptLibraryEntryModel).where(
                    ScriptLibraryEntryModel.id == entry_id,
                    ScriptLibraryEntryModel.organization_id == organization_id,
                )
            )
            entry = result.scalar_one_or_none()
            if entry is None:
                return False
            await session.delete(entry)
            await session.commit()
            return True

    async def get_definition_for_org(
        self, definition_id: int, organization_id: int
    ) -> tuple[WorkflowDefinitionModel, WorkflowModel] | None:
        async with self.async_session() as session:
            result = await session.execute(
                select(WorkflowDefinitionModel, WorkflowModel)
                .join(
                    WorkflowModel,
                    WorkflowDefinitionModel.workflow_id == WorkflowModel.id,
                )
                .where(
                    WorkflowDefinitionModel.id == definition_id,
                    WorkflowModel.organization_id == organization_id,
                )
            )
            row = result.first()
            if not row:
                return None
            return row[0], row[1]

    async def search_prompts_fts(
        self,
        organization_id: int,
        query: str,
        *,
        workflow_id: int | None = None,
        limit: int = 40,
    ) -> list[dict[str, Any]]:
        """Postgres FTS over workflow_definition JSON text, then node-level hits."""
        q = (query or "").strip()
        if not q:
            return []

        async with self.async_session() as session:
            # Rank definitions by full-text match on cast JSON
            ts_query = func.plainto_tsquery("english", q)
            blob = cast(WorkflowDefinitionModel.workflow_json, String)
            ts_vector = func.to_tsvector("english", blob)
            rank = func.ts_rank(ts_vector, ts_query)

            filters = [
                WorkflowModel.organization_id == organization_id,
                or_(
                    ts_vector.op("@@")(ts_query),
                    # Fallback: plain substring when FTS dictionary yields nothing useful
                    blob.ilike(f"%{q}%"),
                ),
            ]
            if workflow_id is not None:
                filters.append(WorkflowModel.id == workflow_id)

            stmt = (
                select(
                    WorkflowDefinitionModel,
                    WorkflowModel,
                    rank.label("rank"),
                )
                .join(
                    WorkflowModel,
                    WorkflowDefinitionModel.workflow_id == WorkflowModel.id,
                )
                .where(*filters)
                .order_by(rank.desc())
                .limit(min(limit * 3, 120))
            )
            rows = (await session.execute(stmt)).all()

        hits: list[dict[str, Any]] = []
        q_lower = q.lower()
        for definition, workflow, rank_val in rows:
            prompts = extract_node_prompts(definition.workflow_json or {})
            for p in prompts:
                text = p["text"]
                if q_lower not in text.lower() and q_lower not in p["node_name"].lower():
                    # still allow FTS-only matches by including first matching prompt
                    # if any token appears
                    tokens = [t for t in q_lower.split() if t]
                    if tokens and not any(t in text.lower() for t in tokens):
                        continue
                excerpt = text.strip().replace("\n", " ")
                if len(excerpt) > 280:
                    excerpt = excerpt[:277] + "..."
                hits.append(
                    {
                        "workflow_id": workflow.id,
                        "workflow_name": workflow.name,
                        "definition_id": definition.id,
                        "version_number": definition.version_number,
                        "version_status": definition.status,
                        "node_id": p["node_id"],
                        "node_name": p["node_name"],
                        "node_type": p["node_type"],
                        "prompt_excerpt": excerpt,
                        "rank": float(rank_val or 0.0),
                    }
                )
                if len(hits) >= limit:
                    return hits
        return hits[:limit]

    async def owner_emails_map(
        self, user_ids: list[int]
    ) -> dict[int, Optional[str]]:
        if not user_ids:
            return {}
        async with self.async_session() as session:
            result = await session.execute(
                select(UserModel).where(UserModel.id.in_(user_ids))
            )
            out: dict[int, Optional[str]] = {}
            for u in result.scalars().all():
                out[u.id] = getattr(u, "email", None) or getattr(u, "provider_id", None)
            return out
