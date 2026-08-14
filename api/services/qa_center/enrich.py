"""Enrich schema-v1 QA with overrides, compliance flags, and review queue rules."""

from __future__ import annotations

from collections import Counter
from typing import Any, Optional

from api.schemas.outcomes import QaRunOutcome
from api.schemas.qa_center import (
    ComplianceFlag,
    ComplianceFlagSummary,
    QaCenterRunRow,
    QaManualOverrideRecord,
    ScoreBucket,
    SentimentBucket,
    TagCount,
)
from api.services.outcomes.normalize import normalize_run_qa
from api.services.qa_center.override import read_override

# Default problem tags from Dograh's default QA system prompt
DEFAULT_PROBLEM_TAGS: list[str] = [
    "DEAD_AIR",
    "USER_FRUSTRATED",
    "ASSISTANT_IN_LOOP",
    "ASSISTANT_REPLY_IMPROPER",
    "USER_NOT_UNDERSTANDING",
    "HEARING_ISSUES",
    "UNCLEAR_CONVERSATION",
    "ASSISTANT_LACKS_EMPATHY",
    "USER_DETECTS_AI",
]

# Known compliance-related raw fields (custom QA prompts / override keys)
COMPLIANCE_FIELD_CATALOG: list[tuple[str, str]] = [
    ("identity_verified", "Identity verified"),
    ("disclosure_made", "Disclosure made"),
    ("recording_notice", "Recording notice"),
    ("dnc_respected", "DNC respected"),
    ("options_presented", "Options presented"),
    ("minors_policy", "Minors policy"),
    ("consent_obtained", "Consent obtained"),
]

# Tag substrings that imply a compliance failure when present
COMPLIANCE_FAIL_TAG_PATTERNS: list[tuple[str, str, str]] = [
    ("IDENTITY", "identity_verified", "Identity-related tag"),
    ("DISCLOSURE", "disclosure_made", "Disclosure-related tag"),
    ("DNC", "dnc_respected", "DNC-related tag"),
    ("CONSENT", "consent_obtained", "Consent-related tag"),
    ("RECORDING_NOTICE", "recording_notice", "Recording-notice tag"),
]

DEFAULT_MAX_SCORE = 6.0  # default QA score scale is 1–10


def _coerce_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        s = value.strip().lower()
        if s in {"true", "yes", "pass", "ok", "1"}:
            return True
        if s in {"false", "no", "fail", "failed", "0"}:
            return False
    return None


def _flag(
    key: str,
    label: str,
    status: str,
    source: str,
    detail: str = "",
) -> ComplianceFlag:
    return ComplianceFlag(
        key=key, label=label, status=status, source=source, detail=detail  # type: ignore[arg-type]
    )


def extract_compliance_flags(
    qa: QaRunOutcome,
    override: Optional[QaManualOverrideRecord] = None,
    annotations: Optional[dict[str, Any]] = None,
) -> list[ComplianceFlag]:
    """Infer compliance flags from override, raw node fields, and problem tags."""
    by_key: dict[str, ComplianceFlag] = {}

    # 1) Seed catalog as unknown
    for key, label in COMPLIANCE_FIELD_CATALOG:
        by_key[key] = _flag(key, label, "unknown", "catalog")

    # 2) Raw fields from QA node results
    for node in qa.nodes:
        raw = node.raw or {}
        # also check nested parsed blobs
        candidates = [raw]
        if isinstance(raw.get("parsed"), dict):
            candidates.append(raw["parsed"])
        for blob in candidates:
            for key, label in COMPLIANCE_FIELD_CATALOG:
                if key not in blob:
                    continue
                b = _coerce_bool(blob.get(key))
                if b is None:
                    continue
                by_key[key] = _flag(
                    key,
                    label,
                    "pass" if b else "fail",
                    "raw_field",
                    detail=f"node={node.node_id}",
                )

    # 3) Tags that imply failure
    for tag in qa.tags:
        upper = tag.upper()
        for pattern, key, detail in COMPLIANCE_FAIL_TAG_PATTERNS:
            if pattern in upper:
                label = dict(COMPLIANCE_FIELD_CATALOG).get(key, key)
                # Only set fail if not already pass from raw field with higher confidence
                existing = by_key.get(key)
                if existing and existing.status == "pass" and existing.source == "raw_field":
                    continue
                by_key[key] = _flag(key, label, "fail", "tag", detail=f"tag={tag}")

    # 4) Manual override wins
    if override and override.compliance_flags:
        for key, val in override.compliance_flags.items():
            label = dict(COMPLIANCE_FIELD_CATALOG).get(key, key.replace("_", " ").title())
            if val is True:
                by_key[key] = _flag(key, label, "pass", "override")
            elif val is False:
                by_key[key] = _flag(key, label, "fail", "override")
            else:
                by_key[key] = _flag(key, label, "unknown", "override")

    # Drop pure-unknown catalog entries that never appeared anywhere
    # Keep ones that were touched by raw/tag/override; always keep if any status != unknown
    # For MVP dashboards show full catalog so ops know what we track.
    _ = annotations  # reserved for future gathered_context hooks
    return list(by_key.values())


def review_reasons(
    *,
    effective_score: Optional[float],
    effective_tags: list[str],
    compliance_flags: list[ComplianceFlag],
    max_score: float,
    problem_tags: list[str],
    has_qa: bool,
    qa_errors: list[str],
) -> list[str]:
    reasons: list[str] = []
    if not has_qa:
        reasons.append("missing_qa")
    if qa_errors:
        reasons.append("qa_errors")
    if effective_score is not None and effective_score <= max_score:
        reasons.append(f"low_score<={max_score}")
    problem_set = {t.upper() for t in problem_tags}
    hit = [t for t in effective_tags if t.upper() in problem_set]
    if hit:
        reasons.append("problem_tags:" + ",".join(hit[:5]))
    fails = [f.key for f in compliance_flags if f.status == "fail"]
    if fails:
        reasons.append("compliance_fail:" + ",".join(fails[:5]))
    return reasons


def build_qa_center_row(
    *,
    run_id: int,
    workflow_id: int,
    workflow_name: str,
    created_at: Any,
    is_completed: bool,
    disposition: str,
    phone_number: str,
    duration_seconds: Optional[float],
    annotations: dict[str, Any] | None,
    max_score: float = DEFAULT_MAX_SCORE,
    problem_tags: Optional[list[str]] = None,
) -> QaCenterRunRow:
    qa = normalize_run_qa(run_id, annotations, workflow_id)
    override = read_override(annotations)
    problem = problem_tags or DEFAULT_PROBLEM_TAGS

    effective_score = (
        override.overall_score if override and override.overall_score is not None else qa.overall_score
    )
    effective_sentiment = (
        override.sentiment if override and override.sentiment else qa.sentiment
    )
    if override and override.tags:
        effective_tags = list(override.tags)
    else:
        effective_tags = list(qa.tags)
    effective_summary = (
        override.summary if override and override.summary else ""
    )
    if not effective_summary and qa.nodes:
        # first non-empty node summary
        for n in qa.nodes:
            if n.summary:
                effective_summary = n.summary
                break

    flags = extract_compliance_flags(qa, override, annotations)
    fail_count = sum(1 for f in flags if f.status == "fail")
    unknown_count = sum(1 for f in flags if f.status == "unknown")
    reasons = review_reasons(
        effective_score=effective_score,
        effective_tags=effective_tags,
        compliance_flags=flags,
        max_score=max_score,
        problem_tags=problem,
        has_qa=qa.has_qa,
        qa_errors=qa.errors,
    )
    # missing_qa alone should not flood the review queue unless requested —
    # keep it but only mark needs_review for actionable issues
    actionable = [r for r in reasons if r != "missing_qa"]
    needs_review = bool(actionable)

    return QaCenterRunRow(
        run_id=run_id,
        workflow_id=workflow_id,
        workflow_name=workflow_name or "",
        created_at=created_at,
        is_completed=bool(is_completed),
        disposition=disposition or "UNKNOWN",
        phone_number=phone_number or "",
        duration_seconds=duration_seconds,
        qa=qa,
        effective_score=effective_score,
        effective_sentiment=effective_sentiment,
        effective_tags=effective_tags,
        effective_summary=effective_summary,
        has_override=override is not None,
        override=override,
        needs_review=needs_review,
        review_reasons=reasons,
        compliance_flags=flags,
        compliance_fail_count=fail_count,
        compliance_unknown_count=unknown_count,
    )


def _score_bucket(score: Optional[float]) -> str:
    if score is None:
        return "unknown"
    if score <= 3:
        return "1-3"
    if score <= 6:
        return "4-6"
    if score <= 8:
        return "7-8"
    return "9-10+"


def summarize_qa_center(
    rows: list[QaCenterRunRow],
    *,
    max_score: float = DEFAULT_MAX_SCORE,
    problem_tags: Optional[list[str]] = None,
) -> dict[str, Any]:
    problem = problem_tags or DEFAULT_PROBLEM_TAGS
    problem_set = {t.upper() for t in problem}
    total = len(rows)
    with_qa = sum(1 for r in rows if r.qa.has_qa)
    scores = [r.effective_score for r in rows if r.effective_score is not None]
    tag_counts: Counter[str] = Counter()
    sent_counts: Counter[str] = Counter()
    score_buckets: Counter[str] = Counter()
    low_score = 0
    problem_tag_runs = 0
    override_count = 0
    needs_review = 0
    compliance_fail_runs = 0
    flag_stats: dict[str, dict[str, int]] = {}

    for r in rows:
        if r.has_override:
            override_count += 1
        if r.needs_review:
            needs_review += 1
        if r.compliance_fail_count > 0:
            compliance_fail_runs += 1
        if r.effective_score is not None and r.effective_score <= max_score:
            low_score += 1
        if any(t.upper() in problem_set for t in r.effective_tags):
            problem_tag_runs += 1
        for t in r.effective_tags:
            tag_counts[t] += 1
        sent = (r.effective_sentiment or "unknown").lower()
        sent_counts[sent] += 1
        score_buckets[_score_bucket(r.effective_score)] += 1
        for f in r.compliance_flags:
            st = flag_stats.setdefault(
                f.key, {"pass": 0, "fail": 0, "unknown": 0, "label": f.label}
            )
            st[f.status] = st.get(f.status, 0) + 1

    compliance_summary = [
        ComplianceFlagSummary(
            key=k,
            label=v.get("label", k),
            pass_count=int(v.get("pass", 0)),
            fail_count=int(v.get("fail", 0)),
            unknown_count=int(v.get("unknown", 0)),
        )
        for k, v in sorted(flag_stats.items())
    ]

    sentiment_distribution = [
        SentimentBucket(
            sentiment=s,
            count=c,
            percentage=round((c / total * 100) if total else 0, 2),
        )
        for s, c in sent_counts.most_common()
    ]
    order = ["1-3", "4-6", "7-8", "9-10+", "unknown"]
    score_distribution = [
        ScoreBucket(bucket=b, count=int(score_buckets.get(b, 0))) for b in order
    ]

    return {
        "total_runs": total,
        "runs_with_qa": with_qa,
        "runs_without_qa": total - with_qa,
        "coverage_pct": round((with_qa / total * 100) if total else 0, 2),
        "average_score": (sum(scores) / len(scores)) if scores else None,
        "low_score_count": low_score,
        "problem_tag_count": problem_tag_runs,
        "override_count": override_count,
        "needs_review_count": needs_review,
        "compliance_fail_runs": compliance_fail_runs,
        "top_tags": [
            TagCount(tag=t, count=c) for t, c in tag_counts.most_common(25)
        ],
        "sentiment_distribution": sentiment_distribution,
        "score_distribution": score_distribution,
        "compliance_summary": compliance_summary,
        "max_score_threshold": max_score,
        "problem_tags": list(problem),
    }
