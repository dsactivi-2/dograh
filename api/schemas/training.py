"""Training / Schulung MVP schemas (P5)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ShadowQuizOption(BaseModel):
    id: str
    label: str


class ShadowQuizQuestion(BaseModel):
    id: str
    prompt: str
    options: list[ShadowQuizOption] = Field(default_factory=list)
    # correct option id(s) — not returned on learner GET (stripped in API)
    correct_option_ids: list[str] = Field(default_factory=list)
    explanation: str = ""


class ShadowContent(BaseModel):
    script_excerpt: str = ""
    learning_points: list[str] = Field(default_factory=list)
    quiz: list[ShadowQuizQuestion] = Field(default_factory=list)


class TextDrillTurn(BaseModel):
    user: str = Field(min_length=1)
    assertions: list[dict[str, Any]] = Field(default_factory=list)


class TextDrillContent(BaseModel):
    """Mirrors TextEvalScenario shape for reuse of the text harness."""

    scenario_name: str = "training-drill"
    initial_context: dict[str, Any] = Field(default_factory=dict)
    turns: list[TextDrillTurn] = Field(default_factory=list)
    final_assertions: list[dict[str, Any]] = Field(default_factory=list)


class TrainingModuleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    mode: Literal["shadow", "text", "voice"] = "shadow"
    workflow_id: Optional[int] = None
    script_entry_id: Optional[int] = None
    success_codes: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    difficulty: Literal["beginner", "intermediate", "advanced"] = "beginner"
    pass_score: float = Field(default=70.0, ge=0, le=100)
    content: dict[str, Any] = Field(default_factory=dict)
    is_published: bool = True


class TrainingModuleUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    mode: Optional[Literal["shadow", "text", "voice"]] = None
    workflow_id: Optional[int] = None
    script_entry_id: Optional[int] = None
    success_codes: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    difficulty: Optional[Literal["beginner", "intermediate", "advanced"]] = None
    pass_score: Optional[float] = Field(default=None, ge=0, le=100)
    content: Optional[dict[str, Any]] = None
    is_published: Optional[bool] = None


class TrainingModuleResponse(BaseModel):
    id: int
    organization_id: int
    title: str
    description: str
    mode: str
    workflow_id: Optional[int] = None
    workflow_name: str = ""
    script_entry_id: Optional[int] = None
    success_codes: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    difficulty: str = "beginner"
    pass_score: float = 70.0
    content: dict[str, Any] = Field(default_factory=dict)
    is_published: bool = True
    created_by_user_id: int
    created_at: Optional[datetime] = None
    # learner progress (optional, filled when requested)
    best_score: Optional[float] = None
    attempts_count: int = 0
    completed: bool = False


class TrainingModuleListResponse(BaseModel):
    total: int
    items: list[TrainingModuleResponse]


class ShadowAnswer(BaseModel):
    question_id: str
    selected_option_ids: list[str] = Field(default_factory=list)


class ShadowCompleteRequest(BaseModel):
    answers: list[ShadowAnswer] = Field(default_factory=list)


class TextDrillRunRequest(BaseModel):
    """Optional overrides when running a text drill (defaults from module content)."""

    initial_context: Optional[dict[str, Any]] = None


class QuizItemResult(BaseModel):
    question_id: str
    correct: bool
    selected: list[str] = Field(default_factory=list)
    expected: list[str] = Field(default_factory=list)
    explanation: str = ""




class VoiceDrillStartRequest(BaseModel):
    """Optional overrides when starting a voice drill session."""

    max_duration_seconds: int = Field(default=90, ge=15, le=180)
    initial_context: Optional[dict[str, Any]] = None


class VoiceDrillStartResponse(BaseModel):
    module_id: int
    workflow_id: int
    workflow_run_id: int
    mode: str = "voice"
    max_duration_hint_seconds: int
    signaling_path: str
    guards: dict[str, Any] = Field(default_factory=dict)
    message: str = (
        "Connect via WebRTC, speak, hang up, then POST .../voice/complete."
    )


class VoiceDrillCompleteRequest(BaseModel):
    workflow_run_id: int
    include_qa: bool = True


class TrainingAttemptResponse(BaseModel):
    id: int
    module_id: int
    module_title: str = ""
    user_id: int
    mode: str
    score: float
    passed: bool
    result: dict[str, Any] = Field(default_factory=dict)
    workflow_run_id: Optional[int] = None
    created_at: Optional[datetime] = None


class TrainingAttemptListResponse(BaseModel):
    total: int
    items: list[TrainingAttemptResponse]


class ModuleProgressItem(BaseModel):
    module_id: int
    title: str
    mode: str
    difficulty: str
    pass_score: float
    attempts_count: int = 0
    best_score: Optional[float] = None
    last_score: Optional[float] = None
    completed: bool = False
    last_attempt_at: Optional[datetime] = None


class TrainingProgressResponse(BaseModel):
    organization_id: int
    user_id: int
    modules_total: int
    modules_completed: int
    completion_pct: float
    average_best_score: Optional[float] = None
    attempts_total: int
    modules: list[ModuleProgressItem] = Field(default_factory=list)
