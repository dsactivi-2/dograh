"""Text-chat eval harness: scenario JSON → turns → assertions."""

from __future__ import annotations

from typing import Any

from loguru import logger

from api.schemas.text_eval import (
    AssertionResult,
    EvalAssertion,
    EvalTurnResult,
    TextEvalRunResponse,
    TextEvalScenario,
)


def evaluate_assertion(
    assertion: EvalAssertion,
    *,
    assistant_text: str,
    gathered: dict[str, Any],
) -> AssertionResult:
    t = assertion.type
    ci = assertion.case_insensitive

    def norm(s: Any) -> str:
        s = "" if s is None else str(s)
        return s.lower() if ci else s

    if t == "response_contains":
        needle = norm(assertion.value)
        hay = norm(assistant_text)
        ok = bool(needle) and needle in hay
        return AssertionResult(
            type=t,
            passed=ok,
            expected=assertion.value,
            actual=assistant_text[:500],
            detail="contains" if ok else "missing substring",
        )
    if t == "response_not_contains":
        needle = norm(assertion.value)
        hay = norm(assistant_text)
        ok = not needle or needle not in hay
        return AssertionResult(
            type=t,
            passed=ok,
            expected=assertion.value,
            actual=assistant_text[:500],
            detail="absent" if ok else "unexpected substring",
        )
    if t == "disposition_equals":
        actual = gathered.get("mapped_call_disposition")
        exp = assertion.value
        ok = norm(actual) == norm(exp)
        return AssertionResult(
            type=t, passed=ok, expected=exp, actual=actual, detail="disposition"
        )
    if t == "gathered_key_exists":
        key = assertion.key or ""
        ok = key in gathered
        return AssertionResult(
            type=t, passed=ok, expected=key, actual=list(gathered.keys())[:20]
        )
    if t == "gathered_key_equals":
        key = assertion.key or ""
        actual = gathered.get(key)
        exp = assertion.value
        ok = norm(actual) == norm(exp)
        return AssertionResult(
            type=t, passed=ok, expected=exp, actual=actual, detail=key
        )
    return AssertionResult(type=t, passed=False, detail="unknown assertion type")


async def run_text_eval_scenario(
    *,
    scenario: TextEvalScenario,
    organization_id: int,
    user_id: int,
    execute_turn,
    create_session,
) -> TextEvalRunResponse:
    """Run scenario using injected session/turn callables (testable).

    create_session(workflow_id, initial_context) -> {workflow_run_id, ...}
    execute_turn(workflow_run_id, text) -> {assistant_text, gathered_context}
    """
    try:
        session = await create_session(scenario.workflow_id, scenario.initial_context)
    except Exception as e:
        logger.exception("eval session create failed")
        return TextEvalRunResponse(
            scenario_name=scenario.name,
            workflow_id=scenario.workflow_id,
            passed=False,
            turns=[],
            error=f"session_create: {e}",
        )

    run_id = session.get("workflow_run_id")
    turn_results: list[EvalTurnResult] = []
    gathered: dict[str, Any] = {}
    last_assistant = ""

    for i, turn in enumerate(scenario.turns):
        try:
            result = await execute_turn(run_id, turn.user)
        except Exception as e:
            logger.exception("eval turn failed")
            turn_results.append(
                EvalTurnResult(
                    index=i,
                    user=turn.user,
                    assistant="",
                    assertions=[
                        AssertionResult(type="turn_error", passed=False, detail=str(e))
                    ],
                    passed=False,
                )
            )
            return TextEvalRunResponse(
                scenario_name=scenario.name,
                workflow_id=scenario.workflow_id,
                workflow_run_id=run_id,
                passed=False,
                turns=turn_results,
                gathered_context=gathered,
                error=f"turn_{i}: {e}",
            )

        last_assistant = str(result.get("assistant_text") or "")
        gathered = result.get("gathered_context") or gathered
        a_results = [
            evaluate_assertion(a, assistant_text=last_assistant, gathered=gathered)
            for a in turn.assertions
        ]
        turn_results.append(
            EvalTurnResult(
                index=i,
                user=turn.user,
                assistant=last_assistant,
                assertions=a_results,
                passed=all(x.passed for x in a_results) if a_results else True,
            )
        )

    final = [
        evaluate_assertion(a, assistant_text=last_assistant, gathered=gathered)
        for a in scenario.final_assertions
    ]
    passed = all(t.passed for t in turn_results) and all(f.passed for f in final)
    return TextEvalRunResponse(
        scenario_name=scenario.name,
        workflow_id=scenario.workflow_id,
        workflow_run_id=run_id,
        passed=passed,
        turns=turn_results,
        final_assertions=final,
        gathered_context=gathered,
    )
