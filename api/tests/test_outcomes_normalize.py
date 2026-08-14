"""Unit tests for Outcomes QA normalizer (no DB)."""

from api.services.outcomes.normalize import normalize_run_qa, summarize_outcomes


def test_normalize_empty_annotations():
    qa = normalize_run_qa(run_id=1, annotations=None, workflow_id=9)
    assert qa.schema_version == 1
    assert qa.run_id == 1
    assert qa.has_qa is False
    assert qa.nodes == []
    assert qa.overall_score is None
    assert qa.sentiment is None


def test_normalize_per_node_scores_and_tags():
    annotations = {
        "qa_node_1": {
            "model": "gpt-4.1",
            "node_results": {
                "n1": {
                    "node_name": "Discovery",
                    "score": 80,
                    "tags": ["good_open", "missed_budget"],
                    "summary": "Solid discovery",
                    "overall_sentiment": "positive",
                },
                "n2": {
                    "node_name": "Close",
                    "score": 60,
                    "tags": ["price_objection"],
                    "summary": "Soft close",
                    "overall_sentiment": "neutral",
                },
            },
        },
        "tags": ["good_open"],
    }
    qa = normalize_run_qa(42, annotations, workflow_id=3)
    assert qa.has_qa is True
    assert qa.workflow_id == 3
    assert len(qa.nodes) == 2
    assert qa.overall_score == 70.0
    assert "good_open" in qa.tags
    assert "price_objection" in qa.tags
    assert "qa_node_1" in qa.source_keys
    assert qa.sentiment in {"positive", "neutral"}  # majority of two distinct = first most_common order


def test_normalize_dict_form_tags():
    annotations = {
        "qa": {
            "node_results": {
                "w": {
                    "node_name": "Whole",
                    "score": 5,
                    "tags": [{"tag": "DEAD_AIR", "reason": "silence"}],
                    "overall_sentiment": "negative",
                }
            }
        }
    }
    qa = normalize_run_qa(1, annotations)
    assert qa.tags == ["DEAD_AIR"]
    assert qa.sentiment == "negative"


def test_normalize_skips_manual_override_key():
    annotations = {
        "qa_manual_override": {
            "overall_score": 9,
            "tags": ["OK"],
        },
        "qa_node": {
            "node_results": {
                "n": {"score": 4, "tags": ["DEAD_AIR"], "overall_sentiment": "negative"}
            }
        },
    }
    qa = normalize_run_qa(1, annotations)
    assert "DEAD_AIR" in qa.tags
    assert "OK" not in qa.tags  # override applied elsewhere
    assert qa.overall_score == 4.0


def test_normalize_tolerates_bad_shapes():
    annotations = {
        "integration_x": {"ok": True},  # no node_results
        "qa_bad": {"node_results": {"x": "not-a-dict"}},
        "tags": "single-tag",
    }
    qa = normalize_run_qa(7, annotations)
    assert qa.has_qa is False or qa.errors  # errors recorded for bad node
    assert any("non-dict" in e for e in qa.errors)


def test_summarize_outcomes_disposition_and_coverage():
    runs = [
        {
            "is_completed": True,
            "disposition": "XFER",
            "qa": {"has_qa": True, "overall_score": 80, "tags": ["a"]},
        },
        {
            "is_completed": False,
            "disposition": "NO_ANSWER",
            "qa": {"has_qa": False, "overall_score": None, "tags": []},
        },
        {
            "is_completed": True,
            "disposition": "XFER",
            "qa": {"has_qa": True, "overall_score": 100, "tags": ["a", "b"]},
        },
    ]
    s = summarize_outcomes(runs)
    assert s["total_runs"] == 3
    assert s["completed_runs"] == 2
    assert s["qa_coverage"]["runs_with_qa"] == 2
    assert s["average_qa_score"] == 90.0
    assert s["disposition_distribution"][0]["disposition"] == "XFER"
