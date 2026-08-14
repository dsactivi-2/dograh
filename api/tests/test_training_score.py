"""Unit tests for training scoring (no DB)."""

from api.services.training.score import (
    score_shadow_quiz,
    score_text_drill,
    strip_quiz_answers,
)


def _shadow_content():
    return {
        "script_excerpt": "Hallo, hier ist Max von Acme…",
        "learning_points": ["Begrüßung", "Identität"],
        "quiz": [
            {
                "id": "q1",
                "prompt": "Was zuerst?",
                "options": [
                    {"id": "a", "label": "Begrüßen"},
                    {"id": "b", "label": "Preis nennen"},
                ],
                "correct_option_ids": ["a"],
                "explanation": "Immer zuerst begrüßen",
            },
            {
                "id": "q2",
                "prompt": "Identität prüfen?",
                "options": [
                    {"id": "yes", "label": "Ja"},
                    {"id": "no", "label": "Nein"},
                ],
                "correct_option_ids": ["yes"],
                "explanation": "Compliance",
            },
        ],
    }


def test_strip_quiz_answers():
    stripped = strip_quiz_answers(_shadow_content())
    for q in stripped["quiz"]:
        assert "correct_option_ids" not in q
        assert "prompt" in q


def test_score_shadow_all_correct():
    r = score_shadow_quiz(
        _shadow_content(),
        [
            {"question_id": "q1", "selected_option_ids": ["a"]},
            {"question_id": "q2", "selected_option_ids": ["yes"]},
        ],
        pass_score=70,
    )
    assert r["score"] == 100.0
    assert r["passed"] is True
    assert r["correct_count"] == 2


def test_score_shadow_partial():
    r = score_shadow_quiz(
        _shadow_content(),
        [{"question_id": "q1", "selected_option_ids": ["a"]}],
        pass_score=70,
    )
    assert r["score"] == 50.0
    assert r["passed"] is False
    assert r["items"][0]["correct"] is True
    assert r["items"][1]["correct"] is False


def test_score_text_drill_assertions_and_disposition():
    assertions = [
        {"type": "response_contains", "passed": True},
        {"type": "response_contains", "passed": True},
        {"type": "disposition_equals", "passed": False},
    ]
    r = score_text_drill(
        eval_passed=False,
        assertion_results=assertions,
        disposition="XFER",
        success_codes=["XFER", "SALE"],
        pass_score=70,
    )
    # assertion 2/3 → 66.67% * 0.8 + 100 * 0.2 ≈ 73.33
    assert r["disposition_success"] is True
    assert r["assertions_passed"] == 2
    expected = round((2 / 3 * 100.0) * 0.8 + 100.0 * 0.2, 2)
    assert r["score"] == expected
    assert r["passed"] is True


def test_score_text_drill_fail_disposition():
    r = score_text_drill(
        eval_passed=True,
        assertion_results=[{"passed": True}, {"passed": True}],
        disposition="NO_ANSWER",
        success_codes=["XFER"],
        pass_score=70,
    )
    # 100*0.8 + 0*0.2 = 80
    assert r["score"] == 80.0
    assert r["disposition_success"] is False
    assert r["passed"] is True


def test_score_text_empty_assertions_uses_eval_flag():
    r = score_text_drill(
        eval_passed=True,
        assertion_results=[],
        disposition=None,
        success_codes=[],
        pass_score=70,
    )
    assert r["score"] == 100.0
    assert r["passed"] is True
