"""Unit tests for cost attribution extraction/aggregation (no DB)."""

from api.services.cost_attribution.extract import extract_run_cost, summarize_cost_rows


def test_extract_empty():
    c = extract_run_cost(None, None)
    assert c["has_cost"] is False
    assert c["duration_seconds"] == 0.0
    assert c["attributed_usd"] is None


def test_extract_charge_and_duration():
    c = extract_run_cost(
        {"charge_usd": 0.12, "dograh_token_usage": 12},
        {"call_duration_seconds": 45},
    )
    assert c["has_cost"] is True
    assert c["charge_usd"] == 0.12
    assert c["attributed_usd"] == 0.12
    assert c["duration_seconds"] == 45.0
    assert c["dograh_token_usage"] == 12


def test_extract_total_cost_usd_derives_tokens():
    c = extract_run_cost({"total_cost_usd": 0.5}, {})
    assert c["has_cost"] is True
    assert c["total_cost_usd"] == 0.5
    assert c["dograh_token_usage"] == 50.0


def test_extract_tolerates_bad_types():
    c = extract_run_cost({"charge_usd": "nope"}, {"call_duration_seconds": "x"})
    assert c["charge_usd"] is None
    assert c["duration_seconds"] == 0.0


def test_summarize_by_workflow():
    rows = [
        {
            "workflow_id": 1,
            "workflow_name": "Sales A",
            "campaign_id": 10,
            "campaign_name": "C1",
            "definition_id": 100,
            "cost_info": {"total_cost_usd": 1.0},
            "usage_info": {"call_duration_seconds": 60},
        },
        {
            "workflow_id": 1,
            "workflow_name": "Sales A",
            "campaign_id": 10,
            "campaign_name": "C1",
            "definition_id": 100,
            "cost_info": {},
            "usage_info": {"call_duration_seconds": 30},
        },
        {
            "workflow_id": 2,
            "workflow_name": "Support",
            "campaign_id": None,
            "definition_id": 200,
            "cost_info": {"charge_usd": 0.25},
            "usage_info": {"call_duration_seconds": 20},
        },
    ]
    s = summarize_cost_rows(rows, group_by="workflow")
    assert s["total_runs"] == 3
    assert s["runs_with_cost"] == 2
    assert s["runs_missing_cost"] == 1
    assert s["total_cost_usd"] == 1.25
    assert len(s["buckets"]) == 2
    top = s["buckets"][0]
    assert top["workflow_id"] == 1
    assert top["run_count"] == 2
    assert top["runs_missing_cost"] == 1


def test_summarize_by_campaign_unattributed():
    rows = [
        {
            "workflow_id": 1,
            "workflow_name": "W",
            "campaign_id": None,
            "definition_id": None,
            "cost_info": {"charge_usd": 0.1},
            "usage_info": {},
        }
    ]
    s = summarize_cost_rows(rows, group_by="campaign")
    assert s["buckets"][0]["group_type"] == "unattributed"
    assert s["buckets"][0]["label"] == "No campaign"
