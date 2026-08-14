"""Unit tests for Campaign Control Tower aggregation (no DB)."""

from api.services.campaign_ops.aggregate import (
    build_disposition_distribution,
    build_funnel_stages,
    count_connected_runs,
    merge_queued_state_counts,
    parse_circuit_breaker_config,
    parse_retry_config,
)


def test_merge_queued_state_counts():
    totals = merge_queued_state_counts(
        [
            {"state": "queued", "count": 5},
            {"state": "processed", "count": 3},
            {"state": "failed", "count": 1},
            {"state": "processing", "count": 2},
        ]
    )
    assert totals["queued"] == 5
    assert totals["processed"] == 3
    assert totals["failed"] == 1
    assert totals["processing"] == 2
    assert totals["total"] == 11


def test_build_funnel_stages_order():
    stages = build_funnel_stages(
        {"queued": 10, "processing": 1, "processed": 8, "failed": 1, "total": 20},
        runs_total=8,
        runs_connected=5,
        disposition_total=4,
    )
    keys = [s["key"] for s in stages]
    assert keys[0] == "queued"
    assert "connected" in keys
    assert "dispositioned" in keys
    connected = next(s for s in stages if s["key"] == "connected")
    assert connected["count"] == 5


def test_count_connected_runs():
    runs = [
        {"is_completed": True, "duration_seconds": 30, "disposition": "XFER"},
        {"is_completed": True, "duration_seconds": 0, "disposition": "NO_ANSWER"},
        {"is_completed": False, "duration_seconds": None, "disposition": "UNKNOWN"},
        {"is_completed": True, "duration_seconds": 0, "disposition": "SALE"},
    ]
    assert count_connected_runs(runs) == 2  # XFER + SALE


def test_disposition_distribution():
    dist = build_disposition_distribution(["XFER", "XFER", "NO_ANSWER", None])
    assert dist[0]["disposition"] == "XFER"
    assert dist[0]["count"] == 2
    assert any(d["disposition"] == "UNKNOWN" for d in dist)


def test_parse_retry_and_cb():
    retry = parse_retry_config(
        {"enabled": True, "max_retries": 3, "retry_delay_seconds": 60}
    )
    assert retry["enabled"] is True
    assert retry["max_retries"] == 3

    cb = parse_circuit_breaker_config(
        {
            "circuit_breaker": {
                "enabled": True,
                "failure_threshold": 0.4,
                "window_seconds": 90,
                "min_calls_in_window": 10,
            }
        }
    )
    assert cb["enabled"] is True
    assert cb["failure_threshold"] == 0.4
    assert parse_circuit_breaker_config(None)["enabled"] is False
