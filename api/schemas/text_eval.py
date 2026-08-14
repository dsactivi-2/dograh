"""Text-chat eval harness schemas (P2)."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class EvalAssertion(BaseModel):
    type: Literal[
        "response_contains",
        "response_not_contains",
        "disposition_equals",
        "gathered_key_equals",
        "gathered_key_exists",
    ]
    value: Any = None
    key: Optional[str] = None
    case_insensitive: bool = True


class EvalTurn(BaseModel):
    user: str = Field(min_length=1)
    assertions: list[EvalAssertion] = Field(default_factory=list)


class TextEvalScenario(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    workflow_id: int
    initial_context: dict[str, Any] = Field(default_factory=dict)
    turns: list[EvalTurn] = Field(min_length=1)
    final_assertions: list[EvalAssertion] = Field(default_factory=list)
    run_qa: bool = False


class AssertionResult(BaseModel):
    type: str
    passed: bool
    detail: str = ""
    expected: Any = None
    actual: Any = None


class EvalTurnResult(BaseModel):
    index: int
    user: str
    assistant: str = ""
    assertions: list[AssertionResult] = Field(default_factory=list)
    passed: bool = True


class TextEvalRunResponse(BaseModel):
    scenario_name: str
    workflow_id: int
    workflow_run_id: Optional[int] = None
    passed: bool
    turns: list[EvalTurnResult]
    final_assertions: list[AssertionResult] = Field(default_factory=list)
    gathered_context: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
