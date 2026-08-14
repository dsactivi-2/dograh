"""Schemas for Cost Attribution dashboard (P3)."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class CostBucket(BaseModel):
    """One aggregation dimension row (workflow / campaign / definition)."""

    key: str
    label: str
    group_type: Literal["workflow", "campaign", "definition", "unattributed"]
    workflow_id: Optional[int] = None
    campaign_id: Optional[int] = None
    definition_id: Optional[int] = None
    run_count: int = 0
    runs_with_cost: int = 0
    runs_missing_cost: int = 0
    total_duration_seconds: float = 0.0
    total_cost_usd: Optional[float] = None
    total_charge_usd: Optional[float] = None
    total_dograh_tokens: float = 0.0
    avg_cost_usd: Optional[float] = None
    cost_coverage_pct: float = 0.0


class CostAttributionSummary(BaseModel):
    from_date: str
    to_date: str
    timezone: str
    workflow_id: Optional[int] = None
    campaign_id: Optional[int] = None
    group_by: Literal["workflow", "campaign", "definition"] = "workflow"
    total_runs: int = 0
    runs_with_cost: int = 0
    runs_missing_cost: int = 0
    cost_coverage_pct: float = 0.0
    total_duration_seconds: float = 0.0
    total_cost_usd: Optional[float] = None
    total_charge_usd: Optional[float] = None
    total_dograh_tokens: float = 0.0
    buckets: list[CostBucket] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
