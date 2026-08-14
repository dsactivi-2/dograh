"""Lead scoring and status derivation for Stepsales qualification."""

from __future__ import annotations

from typing import Any


def score_lead(payload: dict[str, Any]) -> int:
    """Compute a 0–100 qualification score from structured sales fields."""
    score = 0

    if payload.get("active_hiring"):
        score += 20

    urgency = (payload.get("urgency") or "").lower()
    score += {"high": 25, "medium": 15, "low": 5}.get(urgency, 0)

    interest = (payload.get("interest_level") or "").lower()
    score += {"high": 25, "medium": 15, "low": 5}.get(interest, 0)

    if payload.get("email"):
        score += 10
    if payload.get("phone"):
        score += 5

    roles = payload.get("roles_hiring_for") or []
    if isinstance(roles, list):
        score += min(15, 5 * len(roles))

    budget = (payload.get("budget_signal") or "").lower()
    if budget in {"open", "approved", "yes", "budget_available"}:
        score += 10

    timeline = (payload.get("timeline") or "").lower()
    if any(token in timeline for token in ("sofort", "immediate", "1 week", "2 week", "woche", "asap")):
        score += 10
    elif any(token in timeline for token in ("month", "monat", "30")):
        score += 5

    return max(0, min(100, score))


def status_from_score(score: int) -> str:
    if score >= 70:
        return "qualified"
    if score >= 40:
        return "reached"
    return "new"
