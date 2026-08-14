"""Normalize free-form workflow_run.annotations QA into a stable schema."""

from __future__ import annotations

from collections import Counter
from typing import Any, Optional

from api.schemas.outcomes import QaNodeOutcome, QaRunOutcome


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_tags(value: Any) -> list[str]:
    """Accept string tags or default-QA dict form {tag, reason}."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                out.append(item.strip())
            elif isinstance(item, dict):
                tag = item.get("tag") or item.get("name")
                if tag is not None and str(tag).strip():
                    out.append(str(tag).strip())
        return out
    return []


def _as_str_list(value: Any) -> list[str]:
    return _extract_tags(value)


def _extract_sentiment(result: dict[str, Any]) -> Optional[str]:
    for key in ("overall_sentiment", "sentiment", "call_sentiment"):
        raw = result.get(key)
        if raw is None:
            continue
        s = str(raw).strip().lower()
        if s:
            return s
    return None


def _majority_sentiment(values: list[str]) -> Optional[str]:
    if not values:
        return None
    counts = Counter(values)
    return counts.most_common(1)[0][0]


def normalize_run_qa(
    run_id: int,
    annotations: dict[str, Any] | None,
    workflow_id: int | None = None,
) -> QaRunOutcome:
    """Convert raw annotations JSON into QaRunOutcome (schema_version=1).

    Tolerates missing/partial QA. Never raises on bad shapes.
    Does not apply manual overrides — see qa_center.enrich.
    """
    ann = annotations if isinstance(annotations, dict) else {}
    nodes: list[QaNodeOutcome] = []
    errors: list[str] = []
    source_keys: list[str] = []
    aggregate_tags: list[str] = []
    sentiments: list[str] = []

    # Top-level aggregated tags written by run_integrations
    aggregate_tags.extend(_extract_tags(ann.get("tags")))

    for key, payload in ann.items():
        if key in {"tags", "qa_manual_override", "qa_override_audit"}:
            continue
        if not isinstance(payload, dict):
            continue
        node_results = payload.get("node_results")
        if not isinstance(node_results, dict):
            # Skip pure integration payloads without QA node_results
            continue
        source_keys.append(str(key))
        if payload.get("error"):
            errors.append(f"{key}: {payload.get('error')}")
        for node_id, result in node_results.items():
            if not isinstance(result, dict):
                errors.append(f"{key}/{node_id}: non-dict result")
                continue
            tags = _extract_tags(result.get("tags"))
            aggregate_tags.extend(tags)
            err = result.get("error")
            if err:
                errors.append(f"{key}/{node_id}: {err}")
            sentiment = _extract_sentiment(result)
            if sentiment:
                sentiments.append(sentiment)
            nodes.append(
                QaNodeOutcome(
                    node_id=str(node_id),
                    node_name=str(result.get("node_name") or node_id),
                    score=_as_float(result.get("score")),
                    tags=tags,
                    summary=str(result.get("summary") or ""),
                    sentiment=sentiment,
                    error=str(err) if err else None,
                    raw={
                        k: v
                        for k, v in result.items()
                        if k
                        not in {
                            "node_name",
                            "score",
                            "tags",
                            "summary",
                            "error",
                            "overall_sentiment",
                            "sentiment",
                        }
                    },
                )
            )

    scores = [n.score for n in nodes if n.score is not None]
    overall = sum(scores) / len(scores) if scores else None
    # de-dupe tags preserving order
    seen: set[str] = set()
    tags_unique: list[str] = []
    for t in aggregate_tags:
        if t not in seen:
            seen.add(t)
            tags_unique.append(t)

    return QaRunOutcome(
        schema_version=1,
        run_id=run_id,
        workflow_id=workflow_id,
        has_qa=bool(nodes) or bool(source_keys),
        overall_score=overall,
        sentiment=_majority_sentiment(sentiments),
        tags=tags_unique,
        nodes=nodes,
        errors=errors,
        source_keys=source_keys,
    )


def summarize_outcomes(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate disposition + QA coverage from normalized run dicts."""
    total = len(runs)
    completed = sum(1 for r in runs if r.get("is_completed"))
    disp_counts: Counter[str] = Counter()
    tag_counts: Counter[str] = Counter()
    scores: list[float] = []
    with_qa = 0

    for r in runs:
        disp = r.get("disposition") or "UNKNOWN"
        disp_counts[disp] += 1
        qa = r.get("qa") or {}
        if isinstance(qa, dict) and qa.get("has_qa"):
            with_qa += 1
            if qa.get("overall_score") is not None:
                try:
                    scores.append(float(qa["overall_score"]))
                except (TypeError, ValueError):
                    pass
            for t in qa.get("tags") or []:
                tag_counts[str(t)] += 1

    disposition_distribution = [
        {
            "disposition": d,
            "count": c,
            "percentage": round((c / total * 100) if total else 0, 2),
        }
        for d, c in disp_counts.most_common()
    ]
    top_qa_tags = [
        {"tag": t, "count": c} for t, c in tag_counts.most_common(20)
    ]
    return {
        "total_runs": total,
        "completed_runs": completed,
        "disposition_distribution": disposition_distribution,
        "qa_coverage": {
            "runs_with_qa": with_qa,
            "runs_without_qa": total - with_qa,
            "coverage_pct": round((with_qa / total * 100) if total else 0, 2),
        },
        "average_qa_score": (sum(scores) / len(scores)) if scores else None,
        "top_qa_tags": top_qa_tags,
    }
