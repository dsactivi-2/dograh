"""Disposition taxonomy for workflows (success set + labels)."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class DispositionCodeMeta(BaseModel):
    label: str = ""
    category: Literal["success", "neutral", "failure", "other"] = "other"
    description: str = ""


class DispositionTaxonomy(BaseModel):
    """Backward-compatible extension of call_disposition_codes JSON."""

    disposition_codes: list[str] = Field(default_factory=list)
    success_codes: list[str] = Field(default_factory=list)
    code_meta: dict[str, DispositionCodeMeta] = Field(default_factory=dict)

    @field_validator("disposition_codes", "success_codes", mode="before")
    @classmethod
    def _norm_list(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v.strip() else []
        return [str(x).strip() for x in v if str(x).strip()]


class DispositionTaxonomyUpdate(BaseModel):
    disposition_codes: list[str] = Field(default_factory=list)
    success_codes: list[str] = Field(default_factory=list)
    code_meta: dict[str, DispositionCodeMeta] = Field(default_factory=dict)


class DispositionTaxonomyResponse(BaseModel):
    workflow_id: int
    workflow_name: str
    taxonomy: DispositionTaxonomy


class OrgDispositionSummaryItem(BaseModel):
    code: str
    label: str = ""
    category: str = "other"
    workflow_count: int = 0
    is_success: bool = False


class OrgDispositionSummaryResponse(BaseModel):
    organization_id: int
    codes: list[OrgDispositionSummaryItem]
