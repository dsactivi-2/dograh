"""Defensive cost extraction from workflow_run.cost_info / usage_info.

Does NOT invent a billing engine. Reads whatever fields already exist:
- cost_info.charge_usd
- cost_info.total_cost_usd
- cost_info.dograh_token_usage
- usage_info.call_duration_seconds
"""

from __future__ import annotations

from typing import Any, Iterable, Literal, Mapping, Optional


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def extract_run_cost(
    cost_info: Mapping[str, Any] | None,
    usage_info: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Normalize sparse cost/usage JSON into a stable dict.

    ``has_cost`` is True when any monetary or token field is present and parseable.
    Missing fields stay None / 0 — never fabricated from duration alone here
    (duration-based USD is org pricing and lives on organization_usage).
    """
    cost = dict(cost_info) if isinstance(cost_info, Mapping) else {}
    usage = dict(usage_info) if isinstance(usage_info, Mapping) else {}

    charge_usd = _as_float(cost.get("charge_usd"))
    total_cost_usd = _as_float(cost.get("total_cost_usd"))
    dograh_tokens = _as_float(cost.get("dograh_token_usage"))
    if dograh_tokens is None and total_cost_usd is not None:
        # Legacy shape used by format_public_cost_info: 1 cent ≈ 1 token
        dograh_tokens = round(total_cost_usd * 100, 2)

    duration = _as_float(usage.get("call_duration_seconds"))
    if duration is None:
        duration = _as_float(cost.get("call_duration_seconds"))

    has_cost = any(v is not None and v != 0 for v in (charge_usd, total_cost_usd, dograh_tokens))
    # Also treat non-empty cost_info with zero values as "present but zero"
    if not has_cost and cost:
        has_cost = any(
            k in cost for k in ("charge_usd", "total_cost_usd", "dograh_token_usage")
        )

    # Prefer total_cost_usd for attribution; fall back to charge_usd
    attributed_usd = total_cost_usd if total_cost_usd is not None else charge_usd

    return {
        "has_cost": bool(has_cost),
        "charge_usd": charge_usd,
        "total_cost_usd": total_cost_usd,
        "attributed_usd": attributed_usd,
        "dograh_token_usage": dograh_tokens or 0.0,
        "duration_seconds": duration or 0.0,
    }


GroupBy = Literal["workflow", "campaign", "definition"]


def _group_key(row: Mapping[str, Any], group_by: GroupBy) -> tuple[str, dict[str, Any]]:
    if group_by == "workflow":
        wid = row.get("workflow_id")
        name = row.get("workflow_name") or f"Workflow {wid}"
        return f"workflow:{wid}", {
            "key": f"workflow:{wid}",
            "label": str(name),
            "group_type": "workflow",
            "workflow_id": int(wid) if wid is not None else None,
            "campaign_id": None,
            "definition_id": None,
        }
    if group_by == "campaign":
        cid = row.get("campaign_id")
        if cid is None:
            return "campaign:none", {
                "key": "campaign:none",
                "label": "No campaign",
                "group_type": "unattributed",
                "workflow_id": None,
                "campaign_id": None,
                "definition_id": None,
            }
        name = row.get("campaign_name") or f"Campaign {cid}"
        return f"campaign:{cid}", {
            "key": f"campaign:{cid}",
            "label": str(name),
            "group_type": "campaign",
            "workflow_id": int(row["workflow_id"]) if row.get("workflow_id") else None,
            "campaign_id": int(cid),
            "definition_id": None,
        }
    # definition
    did = row.get("definition_id")
    if did is None:
        return "definition:none", {
            "key": "definition:none",
            "label": "No definition",
            "group_type": "unattributed",
            "workflow_id": int(row["workflow_id"]) if row.get("workflow_id") else None,
            "campaign_id": None,
            "definition_id": None,
        }
    label = row.get("definition_label") or f"Definition {did}"
    return f"definition:{did}", {
        "key": f"definition:{did}",
        "label": str(label),
        "group_type": "definition",
        "workflow_id": int(row["workflow_id"]) if row.get("workflow_id") else None,
        "campaign_id": None,
        "definition_id": int(did),
    }


def summarize_cost_rows(
    rows: Iterable[Mapping[str, Any]],
    group_by: GroupBy = "workflow",
) -> dict[str, Any]:
    """Aggregate extracted cost rows into summary + buckets."""
    buckets: dict[str, dict[str, Any]] = {}
    meta: dict[str, dict[str, Any]] = {}

    total_runs = 0
    runs_with_cost = 0
    runs_missing_cost = 0
    total_duration = 0.0
    sum_cost: Optional[float] = 0.0
    sum_charge: Optional[float] = 0.0
    saw_cost = False
    saw_charge = False
    total_tokens = 0.0

    for row in rows:
        total_runs += 1
        cost = extract_run_cost(row.get("cost_info"), row.get("usage_info"))
        gkey, gmeta = _group_key(row, group_by)
        if gkey not in buckets:
            buckets[gkey] = {
                "run_count": 0,
                "runs_with_cost": 0,
                "runs_missing_cost": 0,
                "total_duration_seconds": 0.0,
                "total_cost_usd": None,
                "total_charge_usd": None,
                "total_dograh_tokens": 0.0,
                "_cost_sum": 0.0,
                "_charge_sum": 0.0,
                "_saw_cost": False,
                "_saw_charge": False,
            }
            meta[gkey] = gmeta
        b = buckets[gkey]
        b["run_count"] += 1
        b["total_duration_seconds"] += float(cost["duration_seconds"] or 0)
        b["total_dograh_tokens"] += float(cost["dograh_token_usage"] or 0)
        total_duration += float(cost["duration_seconds"] or 0)
        total_tokens += float(cost["dograh_token_usage"] or 0)

        if cost["has_cost"]:
            runs_with_cost += 1
            b["runs_with_cost"] += 1
        else:
            runs_missing_cost += 1
            b["runs_missing_cost"] += 1

        if cost["attributed_usd"] is not None:
            b["_cost_sum"] += cost["attributed_usd"]
            b["_saw_cost"] = True
            sum_cost = (sum_cost or 0) + cost["attributed_usd"]
            saw_cost = True
        if cost["charge_usd"] is not None:
            b["_charge_sum"] += cost["charge_usd"]
            b["_saw_charge"] = True
            sum_charge = (sum_charge or 0) + cost["charge_usd"]
            saw_charge = True

    out_buckets = []
    for gkey, b in buckets.items():
        rc = b["run_count"] or 1
        total_cost = round(b["_cost_sum"], 6) if b["_saw_cost"] else None
        total_charge = round(b["_charge_sum"], 6) if b["_saw_charge"] else None
        coverage = round(100.0 * b["runs_with_cost"] / rc, 2)
        avg = round(total_cost / b["runs_with_cost"], 6) if total_cost is not None and b["runs_with_cost"] else None
        out_buckets.append(
            {
                **meta[gkey],
                "run_count": b["run_count"],
                "runs_with_cost": b["runs_with_cost"],
                "runs_missing_cost": b["runs_missing_cost"],
                "total_duration_seconds": round(b["total_duration_seconds"], 2),
                "total_cost_usd": total_cost,
                "total_charge_usd": total_charge,
                "total_dograh_tokens": round(b["total_dograh_tokens"], 2),
                "avg_cost_usd": avg,
                "cost_coverage_pct": coverage,
            }
        )

    # Sort by cost desc, then run_count
    out_buckets.sort(
        key=lambda x: (
            -(x["total_cost_usd"] if x["total_cost_usd"] is not None else -1),
            -x["run_count"],
        )
    )

    notes = []
    if runs_missing_cost:
        notes.append(
            f"{runs_missing_cost} run(s) have no cost_info monetary fields; "
            "totals only include runs with charge_usd / total_cost_usd / dograh_token_usage."
        )
    if not saw_cost and total_runs:
        notes.append(
            "No total_cost_usd/charge_usd found in range — showing duration and tokens only."
        )

    coverage = round(100.0 * runs_with_cost / total_runs, 2) if total_runs else 0.0
    return {
        "total_runs": total_runs,
        "runs_with_cost": runs_with_cost,
        "runs_missing_cost": runs_missing_cost,
        "cost_coverage_pct": coverage,
        "total_duration_seconds": round(total_duration, 2),
        "total_cost_usd": round(sum_cost, 6) if saw_cost else None,
        "total_charge_usd": round(sum_charge, 6) if saw_charge else None,
        "total_dograh_tokens": round(total_tokens, 2),
        "buckets": out_buckets,
        "notes": notes,
    }
