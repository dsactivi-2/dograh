"""Pure aggregation helpers for Campaign Control Tower (no DB/Redis)."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable, Mapping, Optional


# Dispositions that typically mean the call never connected to a human.
_NO_CONNECT_DISPOSITIONS = frozenset(
    {
        "NO_ANSWER",
        "BUSY",
        "FAILED",
        "CANCELLED",
        "CANCELED",
        "VOICEMAIL",
        "MACHINE",
        "UNKNOWN",
        "",
    }
)


def merge_queued_state_counts(
    rows: Iterable[Mapping[str, Any]],
) -> dict[str, int]:
    """Collapse (state, count) style rows into totals by state."""
    totals = {
        "queued": 0,
        "processing": 0,
        "processed": 0,
        "failed": 0,
        "total": 0,
    }
    for row in rows:
        if "state" in row:
            state = str(row.get("state") or "")
            count = int(row.get("count") or 0)
            if state in totals:
                totals[state] += count
            totals["total"] += count
        else:
            for key in ("queued", "processing", "processed", "failed"):
                totals[key] += int(row.get(key) or 0)
            totals["total"] += int(row.get("total") or 0)
    return totals


def build_funnel_stages(
    queued_stats: Mapping[str, int],
    runs_total: int,
    runs_connected: int,
    disposition_total: int,
) -> list[dict[str, Any]]:
    """Build ordered funnel: total queued_runs → dialed → connected → dispositioned."""
    total_entered = int(queued_stats.get("total") or 0)
    if total_entered == 0:
        total_entered = (
            int(queued_stats.get("queued") or 0)
            + int(queued_stats.get("processing") or 0)
            + int(queued_stats.get("processed") or 0)
            + int(queued_stats.get("failed") or 0)
        )
    return [
        {
            "key": "queued",
            "label": "Queued (entered)",
            "count": total_entered,
        },
        {
            "key": "still_queued",
            "label": "Still queued",
            "count": int(queued_stats.get("queued") or 0),
        },
        {
            "key": "processing",
            "label": "Processing",
            "count": int(queued_stats.get("processing") or 0),
        },
        {
            "key": "processed",
            "label": "Processed (dialed)",
            "count": int(queued_stats.get("processed") or 0),
        },
        {
            "key": "connected",
            "label": "Connected runs",
            "count": int(runs_connected),
        },
        {
            "key": "dispositioned",
            "label": "With disposition",
            "count": int(disposition_total),
        },
        {
            "key": "runs_total",
            "label": "Workflow runs",
            "count": int(runs_total),
        },
    ]


def count_connected_runs(
    runs: Iterable[Mapping[str, Any]],
) -> int:
    """Heuristic: completed run with duration > 0 OR disposition not no-connect."""
    connected = 0
    for run in runs:
        if not run.get("is_completed"):
            continue
        duration = run.get("duration_seconds")
        try:
            dur_f = float(duration) if duration is not None else 0.0
        except (TypeError, ValueError):
            dur_f = 0.0
        disposition = str(run.get("disposition") or "UNKNOWN").upper()
        if dur_f > 0:
            connected += 1
        elif disposition not in _NO_CONNECT_DISPOSITIONS:
            connected += 1
    return connected


def build_disposition_distribution(
    dispositions: Iterable[Optional[str]],
) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for d in dispositions:
        key = str(d).strip() if d else "UNKNOWN"
        if not key:
            key = "UNKNOWN"
        counter[key] += 1
    total = sum(counter.values()) or 1
    return [
        {
            "disposition": code,
            "count": count,
            "percentage": round(100.0 * count / total, 2),
        }
        for code, count in counter.most_common()
    ]


def parse_retry_config(retry_config: Any) -> dict[str, Any]:
    if not isinstance(retry_config, dict):
        return {
            "enabled": False,
            "max_retries": 0,
            "retry_delay_seconds": 0,
        }
    return {
        "enabled": bool(retry_config.get("enabled", False)),
        "max_retries": int(retry_config.get("max_retries") or 0),
        "retry_delay_seconds": int(retry_config.get("retry_delay_seconds") or 0),
    }


def parse_circuit_breaker_config(meta: Any) -> dict[str, Any]:
    if not isinstance(meta, dict):
        return {
            "enabled": False,
            "failure_threshold": 0.5,
            "window_seconds": 120,
            "min_calls_in_window": 5,
        }
    cb = meta.get("circuit_breaker") if "circuit_breaker" in meta else meta
    if not isinstance(cb, dict):
        return {
            "enabled": False,
            "failure_threshold": 0.5,
            "window_seconds": 120,
            "min_calls_in_window": 5,
        }
    return {
        "enabled": bool(cb.get("enabled", False)),
        "failure_threshold": float(cb.get("failure_threshold", 0.5)),
        "window_seconds": int(cb.get("window_seconds", 120)),
        "min_calls_in_window": int(cb.get("min_calls_in_window", 5)),
    }
