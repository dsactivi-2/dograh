"""Unit tests for QA Center enrich + override (no DB)."""

from api.services.outcomes.normalize import normalize_run_qa
from api.services.qa_center.enrich import (
    build_qa_center_row,
    extract_compliance_flags,
    summarize_qa_center,
)
from api.services.qa_center.override import apply_manual_override, read_override
from api.schemas.qa_center import QaManualOverridePayload


def _qa_annotations(score=4, tags=None, sentiment="negative"):
    tags = tags or [
        {"tag": "USER_FRUSTRATED", "reason": "yelled"},
        {"tag": "DEAD_AIR", "reason": "long silence"},
    ]
    return {
        "qa_node_1": {
            "model": "gpt-4.1",
            "node_results": {
                "whole_call": {
                    "node_name": "Whole call",
                    "score": score,
                    "tags": tags,
                    "summary": "Rough call",
                    "overall_sentiment": sentiment,
                    "identity_verified": False,
                    "disclosure_made": True,
                }
            },
        },
        "tags": ["USER_FRUSTRATED", "DEAD_AIR"],
    }


def test_normalize_dict_tags_and_sentiment():
    qa = normalize_run_qa(1, _qa_annotations())
    assert qa.has_qa is True
    assert "USER_FRUSTRATED" in qa.tags
    assert "DEAD_AIR" in qa.tags
    assert qa.sentiment == "negative"
    assert qa.overall_score == 4.0
    assert qa.nodes[0].sentiment == "negative"


def test_compliance_from_raw_fields_and_tags():
    qa = normalize_run_qa(2, _qa_annotations())
    flags = extract_compliance_flags(qa)
    by_key = {f.key: f for f in flags}
    assert by_key["identity_verified"].status == "fail"
    assert by_key["identity_verified"].source == "raw_field"
    assert by_key["disclosure_made"].status == "pass"


def test_override_wins_and_audit():
    ann = _qa_annotations()
    patch = apply_manual_override(
        ann,
        QaManualOverridePayload(
            overall_score=8,
            sentiment="neutral",
            tags=["REVIEWED_OK"],
            summary="Human reviewed — fine",
            notes="False positive frustration",
            compliance_flags={"identity_verified": True, "disclosure_made": True},
        ),
        reviewer_user_id=42,
        reviewer_email="rev@example.com",
    )
    merged = {**ann, **patch}
    rec = read_override(merged)
    assert rec is not None
    assert rec.overall_score == 8
    assert rec.reviewer_user_id == 42
    assert "qa_override_audit" in patch
    assert len(patch["qa_override_audit"]) == 1

    row = build_qa_center_row(
        run_id=9,
        workflow_id=1,
        workflow_name="Agent",
        created_at=None,
        is_completed=True,
        disposition="XFER",
        phone_number="+1",
        duration_seconds=30,
        annotations=merged,
        max_score=6,
    )
    assert row.has_override is True
    assert row.effective_score == 8
    assert row.effective_tags == ["REVIEWED_OK"]
    by_key = {f.key: f for f in row.compliance_flags}
    assert by_key["identity_verified"].status == "pass"
    assert by_key["identity_verified"].source == "override"
    # score 8 > 6 and override fixed compliance → may still need_review if problem tags?
    # override replaced tags so no problem tags; score ok → no review
    assert row.needs_review is False


def test_review_queue_low_score_and_problem_tags():
    row = build_qa_center_row(
        run_id=3,
        workflow_id=1,
        workflow_name="A",
        created_at=None,
        is_completed=True,
        disposition="NO_ANSWER",
        phone_number="",
        duration_seconds=12,
        annotations=_qa_annotations(score=3),
        max_score=6,
    )
    assert row.needs_review is True
    assert any("low_score" in r for r in row.review_reasons)
    assert any("problem_tags" in r for r in row.review_reasons)
    assert any("compliance_fail" in r for r in row.review_reasons)


def test_summarize_aggregates():
    rows = [
        build_qa_center_row(
            run_id=i,
            workflow_id=1,
            workflow_name="A",
            created_at=None,
            is_completed=True,
            disposition="XFER",
            phone_number="",
            duration_seconds=10,
            annotations=_qa_annotations(score=score, sentiment=sent),
            max_score=6,
        )
        for i, (score, sent) in enumerate([(3, "negative"), (9, "positive"), (5, "neutral")], start=1)
    ]
    s = summarize_qa_center(rows, max_score=6)
    assert s["total_runs"] == 3
    assert s["runs_with_qa"] == 3
    assert s["low_score_count"] == 2  # 3 and 5
    assert s["average_score"] == (3 + 9 + 5) / 3
    assert s["needs_review_count"] >= 2
    sentiments = {b.sentiment: b.count for b in s["sentiment_distribution"]}
    assert sentiments.get("negative") == 1
    assert sentiments.get("positive") == 1


def test_second_override_chains_previous():
    ann = _qa_annotations()
    p1 = apply_manual_override(
        ann,
        QaManualOverridePayload(overall_score=5, notes="first"),
        reviewer_user_id=1,
    )
    merged = {**ann, **p1}
    p2 = apply_manual_override(
        merged,
        QaManualOverridePayload(overall_score=9, notes="second"),
        reviewer_user_id=2,
    )
    final = {**merged, **p2}
    rec = read_override(final)
    assert rec.overall_score == 9
    assert rec.previous is not None
    assert rec.previous.get("overall_score") == 5
    assert len(final["qa_override_audit"]) == 2
