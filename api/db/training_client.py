"""DB access for Training modules + attempts (P5)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select

from api.db.base_client import BaseDBClient
from api.db.models import TrainingAttemptModel, TrainingModuleModel, WorkflowModel


class TrainingClient(BaseDBClient):
    async def create_training_module(
        self,
        *,
        organization_id: int,
        title: str,
        created_by_user_id: int,
        description: str = "",
        mode: str = "shadow",
        workflow_id: Optional[int] = None,
        script_entry_id: Optional[int] = None,
        success_codes: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        difficulty: str = "beginner",
        pass_score: float = 70.0,
        content: Optional[dict[str, Any]] = None,
        is_published: bool = True,
    ) -> TrainingModuleModel:
        async with self.async_session() as session:
            if workflow_id is not None:
                wf = await session.execute(
                    select(WorkflowModel).where(
                        WorkflowModel.id == workflow_id,
                        WorkflowModel.organization_id == organization_id,
                    )
                )
                if wf.scalar_one_or_none() is None:
                    raise ValueError("Workflow not found in organization")

            row = TrainingModuleModel(
                organization_id=organization_id,
                title=title.strip(),
                description=description or "",
                mode=mode,
                workflow_id=workflow_id,
                script_entry_id=script_entry_id,
                success_codes=list(success_codes or []),
                tags=list(tags or []),
                difficulty=difficulty,
                pass_score=float(pass_score),
                content=dict(content or {}),
                is_published=bool(is_published),
                created_by_user_id=created_by_user_id,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return row

    async def get_training_module(
        self, module_id: int, organization_id: int
    ) -> TrainingModuleModel | None:
        async with self.async_session() as session:
            result = await session.execute(
                select(TrainingModuleModel).where(
                    TrainingModuleModel.id == module_id,
                    TrainingModuleModel.organization_id == organization_id,
                )
            )
            return result.scalar_one_or_none()

    async def list_training_modules(
        self,
        organization_id: int,
        *,
        mode: Optional[str] = None,
        published_only: bool = False,
        page: int = 1,
        limit: int = 50,
    ) -> tuple[list[TrainingModuleModel], int]:
        async with self.async_session() as session:
            filters = [TrainingModuleModel.organization_id == organization_id]
            if mode:
                filters.append(TrainingModuleModel.mode == mode)
            if published_only:
                filters.append(TrainingModuleModel.is_published.is_(True))

            total = int(
                (
                    await session.execute(
                        select(func.count(TrainingModuleModel.id)).where(*filters)
                    )
                ).scalar_one()
            )
            offset = max(0, (page - 1) * limit)
            result = await session.execute(
                select(TrainingModuleModel)
                .where(*filters)
                .order_by(TrainingModuleModel.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            return list(result.scalars().all()), total

    async def update_training_module(
        self, module_id: int, organization_id: int, **fields: Any
    ) -> TrainingModuleModel | None:
        async with self.async_session() as session:
            result = await session.execute(
                select(TrainingModuleModel).where(
                    TrainingModuleModel.id == module_id,
                    TrainingModuleModel.organization_id == organization_id,
                )
            )
            row = result.scalar_one_or_none()
            if row is None:
                return None
            allowed = {
                "title",
                "description",
                "mode",
                "workflow_id",
                "script_entry_id",
                "success_codes",
                "tags",
                "difficulty",
                "pass_score",
                "content",
                "is_published",
            }
            for k, v in fields.items():
                if k in allowed and v is not None:
                    if k == "title":
                        setattr(row, k, str(v).strip())
                    else:
                        setattr(row, k, v)
            row.updated_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(row)
            return row

    async def delete_training_module(
        self, module_id: int, organization_id: int
    ) -> bool:
        async with self.async_session() as session:
            result = await session.execute(
                select(TrainingModuleModel).where(
                    TrainingModuleModel.id == module_id,
                    TrainingModuleModel.organization_id == organization_id,
                )
            )
            row = result.scalar_one_or_none()
            if row is None:
                return False
            await session.delete(row)
            await session.commit()
            return True

    async def create_training_attempt(
        self,
        *,
        organization_id: int,
        module_id: int,
        user_id: int,
        mode: str,
        score: float,
        passed: bool,
        result: Optional[dict[str, Any]] = None,
        workflow_run_id: Optional[int] = None,
    ) -> TrainingAttemptModel:
        async with self.async_session() as session:
            row = TrainingAttemptModel(
                organization_id=organization_id,
                module_id=module_id,
                user_id=user_id,
                mode=mode,
                score=float(score),
                passed=bool(passed),
                result=dict(result or {}),
                workflow_run_id=workflow_run_id,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return row

    async def list_training_attempts(
        self,
        organization_id: int,
        *,
        user_id: Optional[int] = None,
        module_id: Optional[int] = None,
        page: int = 1,
        limit: int = 50,
    ) -> tuple[list[TrainingAttemptModel], int]:
        async with self.async_session() as session:
            filters = [TrainingAttemptModel.organization_id == organization_id]
            if user_id is not None:
                filters.append(TrainingAttemptModel.user_id == user_id)
            if module_id is not None:
                filters.append(TrainingAttemptModel.module_id == module_id)
            total = int(
                (
                    await session.execute(
                        select(func.count(TrainingAttemptModel.id)).where(*filters)
                    )
                ).scalar_one()
            )
            offset = max(0, (page - 1) * limit)
            result = await session.execute(
                select(TrainingAttemptModel)
                .where(*filters)
                .order_by(TrainingAttemptModel.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            return list(result.scalars().all()), total

    async def get_user_module_stats(
        self, organization_id: int, user_id: int
    ) -> dict[int, dict[str, Any]]:
        """Return {module_id: {attempts, best_score, last_score, last_at, completed}}."""
        async with self.async_session() as session:
            result = await session.execute(
                select(TrainingAttemptModel)
                .where(
                    TrainingAttemptModel.organization_id == organization_id,
                    TrainingAttemptModel.user_id == user_id,
                )
                .order_by(TrainingAttemptModel.created_at.desc())
            )
            stats: dict[int, dict[str, Any]] = {}
            for att in result.scalars().all():
                mid = int(att.module_id)
                if mid not in stats:
                    stats[mid] = {
                        "attempts_count": 0,
                        "best_score": None,
                        "last_score": float(att.score),
                        "last_attempt_at": att.created_at,
                        "completed": False,
                    }
                s = stats[mid]
                s["attempts_count"] += 1
                if s["best_score"] is None or att.score > s["best_score"]:
                    s["best_score"] = float(att.score)
                if att.passed:
                    s["completed"] = True
            return stats
