"""Schemas for Campaign Control Tower (P3)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class FunnelStage(BaseModel):
    """One stage of the campaign dial funnel."""

    key: str
    label: str
    count: int = 0


class DispositionBucket(BaseModel):
    disposition: str
    count: int
    percentage: float = 0.0


class RetryVisibility(BaseModel):
    """Retry config + counts derived from queued_runs."""

    enabled: bool = False
    max_retries: int = 0
    retry_delay_seconds: int = 0
    total_with_retry: int = 0
    max_observed_retry_count: int = 0
    by_reason: dict[str, int] = Field(default_factory=dict)


class CircuitBreakerVisibility(BaseModel):
    """Circuit-breaker config + best-effort live window (Redis if available)."""

    enabled: bool = False
    failure_threshold: float = 0.5
    window_seconds: int = 120
    min_calls_in_window: int = 5
    # Live window (None when Redis unavailable or CB disabled)
    is_open: Optional[bool] = None
    failure_count: Optional[int] = None
    success_count: Optional[int] = None
    failure_rate: Optional[float] = None
    source: str = "config"  # config | redis | unavailable


class CampaignOpsRow(BaseModel):
    campaign_id: int
    campaign_name: str
    workflow_id: int
    workflow_name: str
    state: str
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_rows: Optional[int] = None
    processed_rows: int = 0
    failed_rows: int = 0
    # queued_runs funnel
    queued: int = 0
    processing: int = 0
    processed: int = 0
    failed_queued: int = 0
    total_queued_runs: int = 0
    # workflow_runs for this campaign
    runs_total: int = 0
    runs_completed: int = 0
    runs_connected: int = 0  # completed with duration > 0 or disposition not terminal-no-connect
    disposition_distribution: list[DispositionBucket] = Field(default_factory=list)
    retry: RetryVisibility = Field(default_factory=RetryVisibility)
    circuit_breaker: CircuitBreakerVisibility = Field(
        default_factory=CircuitBreakerVisibility
    )
    recent_logs: list[dict[str, Any]] = Field(default_factory=list)


class CampaignOpsSummary(BaseModel):
    from_date: str
    to_date: str
    timezone: str
    campaign_id: Optional[int] = None
    workflow_id: Optional[int] = None
    campaign_count: int = 0
    funnel: list[FunnelStage] = Field(default_factory=list)
    disposition_distribution: list[DispositionBucket] = Field(default_factory=list)
    totals: dict[str, int] = Field(default_factory=dict)
    campaigns: list[CampaignOpsRow] = Field(default_factory=list)
