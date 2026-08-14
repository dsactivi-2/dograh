"""Script library API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


ApprovalStatus = Literal["draft", "pending", "approved", "rejected"]


class ScriptEntryCreate(BaseModel):
    workflow_id: int
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    definition_id: Optional[int] = None


class ScriptEntryUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    tags: Optional[list[str]] = None
    definition_id: Optional[int] = None
    approval_status: Optional[ApprovalStatus] = None


class ScriptEntryResponse(BaseModel):
    id: int
    organization_id: int
    workflow_id: int
    workflow_name: str = ""
    definition_id: Optional[int] = None
    title: str
    description: str
    tags: list[str]
    owner_user_id: int
    owner_email: Optional[str] = None
    approval_status: ApprovalStatus
    approved_by_user_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class ScriptListResponse(BaseModel):
    total: int
    items: list[ScriptEntryResponse]


class PromptSearchHit(BaseModel):
    workflow_id: int
    workflow_name: str
    definition_id: int
    version_number: Optional[int] = None
    version_status: Optional[str] = None
    node_id: str
    node_name: str
    node_type: str
    prompt_excerpt: str
    rank: float = 0.0


class PromptSearchResponse(BaseModel):
    query: str
    total: int
    hits: list[PromptSearchHit]


class PromptDiffLine(BaseModel):
    node_id: str
    node_name: str
    field: str
    before: str = ""
    after: str = ""
    change: Literal["added", "removed", "changed", "unchanged"]


class DefinitionDiffResponse(BaseModel):
    definition_a_id: int
    definition_b_id: int
    workflow_id_a: Optional[int] = None
    workflow_id_b: Optional[int] = None
    changes: list[PromptDiffLine]
    summary: dict[str, int]
