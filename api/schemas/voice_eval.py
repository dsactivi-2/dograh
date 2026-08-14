"""Voice eval schemas (P6) — score completed runs + guarded WebRTC sessions."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class VoiceScoreRunRequest(BaseModel):
    """Score an existing workflow run (typically SMALLWEBRTC / telephony)."""

    workflow_run_id: int
    assertions: list[dict[str, Any]] = Field(default_factory=list)
    success_codes: list[str] = Field(default_factory=list)
    pass_score: float = Field(default=70.0, ge=0, le=100)
    include_qa: bool = True


class VoiceScoreRunResponse(BaseModel):
    mode: str = "voice"
    run_id: int
    workflow_id: Optional[int] = None
    run_mode: Optional[str] = None
    is_completed: bool = False
    score: float
    passed: bool
    pass_score: float = 70.0
    transcript: str = ""
    transcript_chars: int = 0
    has_transcript: bool = False
    disposition: Optional[str] = None
    disposition_success: bool = False
    success_codes: list[str] = Field(default_factory=list)
    assertions_total: int = 0
    assertions_passed: int = 0
    assertion_pass_rate: Optional[float] = None
    assertion_results: list[dict[str, Any]] = Field(default_factory=list)
    qa_score: Optional[float] = None
    qa_tags: list[str] = Field(default_factory=list)
    qa: Optional[dict[str, Any]] = None
    error: Optional[str] = None


class VoiceSessionCreateRequest(BaseModel):
    """Create a short SMALLWEBRTC run for human-in-the-loop voice eval."""

    workflow_id: int
    scenario_name: str = Field(default="voice-eval", max_length=200)
    initial_context: dict[str, Any] = Field(default_factory=dict)
    # Hint only — pipeline still uses definition max_call_duration; UI should hang up.
    max_duration_seconds: int = Field(default=90, ge=15, le=180)
    assertions: list[dict[str, Any]] = Field(default_factory=list)
    success_codes: list[str] = Field(default_factory=list)
    pass_score: float = Field(default=70.0, ge=0, le=100)
    # Optional link to script library / training
    script_entry_id: Optional[int] = None
    tags: list[str] = Field(default_factory=list)


class VoiceSessionCreateResponse(BaseModel):
    workflow_id: int
    workflow_run_id: int
    mode: str = "smallwebrtc"
    scenario_name: str
    max_duration_hint_seconds: int
    signaling_path: str
    # Client connects via existing WS: /api/v1/ws/signaling/{workflow_id}/{run_id}
    guards: dict[str, Any] = Field(default_factory=dict)
    assertions: list[dict[str, Any]] = Field(default_factory=list)
    success_codes: list[str] = Field(default_factory=list)
    pass_score: float = 70.0
    message: str = (
        "Connect via WebRTC signaling, speak briefly, hang up, then call finalize."
    )


class VoiceSessionFinalizeRequest(BaseModel):
    assertions: list[dict[str, Any]] = Field(default_factory=list)
    success_codes: list[str] = Field(default_factory=list)
    pass_score: float = Field(default=70.0, ge=0, le=100)
    include_qa: bool = True


class VoiceSessionFinalizeResponse(VoiceScoreRunResponse):
    scenario_name: Optional[str] = None
    signaling_path: Optional[str] = None
