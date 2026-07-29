"""Unit tests for voice eval scoring + cost guards (no DB)."""

import os

from api.schemas.text_eval import EvalAssertion
from api.services.evals.voice_guards import (
    VOICE_EVAL_HARD_MAX_DURATION_SECONDS,
    VOICE_EVAL_MAX_BATCH,
    VOICE_EVAL_MAX_DURATION_HINT_SECONDS,
    VOICE_EVAL_MAX_SESSIONS_PER_ORG_HOUR,
    VoiceEvalGuardError,
    check_voice_eval_allowed,
    clamp_max_duration_seconds,
    http_status_for_guard,
    public_guard_config,
    resolve_voice_eval_duration_cap,
)
from api.services.evals.voice_score import (
    extract_transcript,
    run_assertions_on_transcript,
    score_voice_run,
)
from api.services.training.score import score_voice_drill


def _rtf_logs():
    return {
        "realtime_feedback_events": [
            {
                "type": "rtf-user-transcription",
                "payload": {"final": True, "text": "Hallo?", "timestamp": "0"},
            },
            {
                "type": "rtf-bot-text",
                "payload": {
                    "text": "Hallo, hier ist Max von Acme.",
                    "timestamp": "1",
                },
            },
            {
                "type": "rtf-user-transcription",
                "payload": {"final": False, "text": "partial"},  # ignored
            },
        ]
    }


def test_extract_transcript():
    t = extract_transcript(_rtf_logs())
    assert "user: Hallo?" in t
    assert "assistant: Hallo, hier ist Max von Acme." in t
    assert "partial" not in t


def test_assertions_on_transcript():
    results = run_assertions_on_transcript(
        [
            EvalAssertion(type="response_contains", value="acme", case_insensitive=True),
            EvalAssertion(type="disposition_equals", value="XFER"),
        ],
        transcript=extract_transcript(_rtf_logs()),
        gathered={"mapped_call_disposition": "XFER"},
    )
    assert results[0].passed is True
    assert results[1].passed is True


def test_score_voice_run_with_assertions_and_disposition():
    scored = score_voice_run(
        run_id=1,
        workflow_id=9,
        mode="smallwebrtc",
        is_completed=True,
        logs=_rtf_logs(),
        gathered_context={"mapped_call_disposition": "XFER"},
        annotations={},
        assertions=[
            {"type": "response_contains", "value": "Max", "case_insensitive": True}
        ],
        success_codes=["XFER", "SALE"],
        pass_score=70,
        include_qa=False,
    )
    assert scored["has_transcript"] is True
    assert scored["disposition_success"] is True
    assert scored["assertions_passed"] == 1
    assert scored["score"] >= 70
    assert scored["passed"] is True
    assert scored["mode"] == "voice"


def test_score_voice_run_fail_no_transcript():
    scored = score_voice_run(
        run_id=2,
        workflow_id=9,
        mode="smallwebrtc",
        is_completed=False,
        logs={},
        gathered_context={},
        annotations={},
        assertions=[],
        success_codes=["XFER"],
        pass_score=70,
        include_qa=False,
    )
    assert scored["score"] == 0.0
    assert scored["passed"] is False
    assert scored["has_transcript"] is False


def test_score_voice_drill_adapter():
    raw = score_voice_run(
        run_id=3,
        workflow_id=1,
        mode="smallwebrtc",
        is_completed=True,
        logs=_rtf_logs(),
        gathered_context={"mapped_call_disposition": "XFER"},
        annotations={},
        assertions=[],
        success_codes=["XFER"],
        pass_score=70,
        include_qa=False,
    )
    drill = score_voice_drill(voice_score_payload=raw, pass_score=70)
    assert drill["mode"] == "voice"
    assert drill["passed"] is True


def test_clamp_duration():
    assert clamp_max_duration_seconds(None) == VOICE_EVAL_MAX_DURATION_HINT_SECONDS
    assert clamp_max_duration_seconds(30) == 30
    assert (
        clamp_max_duration_seconds(999) == VOICE_EVAL_HARD_MAX_DURATION_SECONDS
    )
    assert clamp_max_duration_seconds(-5) == VOICE_EVAL_MAX_DURATION_HINT_SECONDS


def test_resolve_duration_cap_from_initial_context():
    assert resolve_voice_eval_duration_cap(None) is None
    assert resolve_voice_eval_duration_cap({}) is None
    assert (
        resolve_voice_eval_duration_cap(
            {"voice_eval": {"max_duration_hint_seconds": 45}}
        )
        == 45
    )
    assert (
        resolve_voice_eval_duration_cap(
            {"training_voice": {"max_duration_hint_seconds": 999}}
        )
        == VOICE_EVAL_HARD_MAX_DURATION_SECONDS
    )


def test_guard_rate_limit():
    ok = check_voice_eval_allowed(recent_session_count=0, batch_size=1)
    assert ok["allowed"] is True
    assert ok["pipeline_duration_cap"] is True
    try:
        check_voice_eval_allowed(
            recent_session_count=VOICE_EVAL_MAX_SESSIONS_PER_ORG_HOUR,
            batch_size=1,
        )
        assert False, "expected rate limit"
    except VoiceEvalGuardError as e:
        assert e.code == "rate_limited"
        assert http_status_for_guard(e.code) == 429


def test_guard_batch():
    try:
        check_voice_eval_allowed(
            recent_session_count=0, batch_size=VOICE_EVAL_MAX_BATCH + 1
        )
        assert False, "expected batch error"
    except VoiceEvalGuardError as e:
        assert e.code == "batch_too_large"
        assert http_status_for_guard(e.code) == 400


def test_guard_feature_flag():
    try:
        check_voice_eval_allowed(feature_enabled=False)
        assert False
    except VoiceEvalGuardError as e:
        assert e.code == "feature_disabled"
        assert http_status_for_guard(e.code) == 403


def test_public_guard_config():
    cfg = public_guard_config()
    assert "enabled" in cfg
    assert cfg["max_batch"] == 1
    assert "VOICE_EVAL_ENABLED" in cfg["env_keys"]
