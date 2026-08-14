"""Unit tests for text eval assertions + injectable harness (no live LLM)."""

import asyncio

from api.schemas.text_eval import EvalAssertion, EvalTurn, TextEvalScenario
from api.services.evals.text_harness import evaluate_assertion, run_text_eval_scenario


def test_response_contains_ci():
    r = evaluate_assertion(
        EvalAssertion(type="response_contains", value="Hello", case_insensitive=True),
        assistant_text="well hello there",
        gathered={},
    )
    assert r.passed is True


def test_disposition_and_gathered():
    g = {"mapped_call_disposition": "XFER", "budget": "high"}
    assert evaluate_assertion(
        EvalAssertion(type="disposition_equals", value="xfer"),
        assistant_text="",
        gathered=g,
    ).passed
    assert evaluate_assertion(
        EvalAssertion(type="gathered_key_exists", key="budget"),
        assistant_text="",
        gathered=g,
    ).passed
    assert evaluate_assertion(
        EvalAssertion(type="gathered_key_equals", key="budget", value="high"),
        assistant_text="",
        gathered=g,
    ).passed


def test_run_scenario_injectable():
    async def create_session(wf_id, ctx):
        return {"workflow_run_id": 99}

    async def execute_turn(run_id, text):
        return {
            "assistant_text": f"Echo: {text}",
            "gathered_context": {"mapped_call_disposition": "XFER"},
        }

    scenario = TextEvalScenario(
        name="echo",
        workflow_id=1,
        turns=[
            EvalTurn(
                user="hi",
                assertions=[
                    EvalAssertion(type="response_contains", value="hi"),
                ],
            )
        ],
        final_assertions=[
            EvalAssertion(type="disposition_equals", value="XFER"),
        ],
    )

    result = asyncio.run(
        run_text_eval_scenario(
            scenario=scenario,
            organization_id=1,
            user_id=1,
            execute_turn=execute_turn,
            create_session=create_session,
        )
    )
    assert result.passed is True
    assert result.workflow_run_id == 99
    assert result.turns[0].assistant.startswith("Echo")
