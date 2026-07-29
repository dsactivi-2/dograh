"""Cost / safety guards for voice eval + training voice (P6).

Voice runs are expensive (STT+LLM+TTS). These pure helpers enforce hard
limits; callers supply recent-session counts from the DB.

Env (optional, process-level):
  VOICE_EVAL_ENABLED=true|false
  VOICE_EVAL_MAX_SESSIONS_PER_ORG_HOUR=5
  VOICE_EVAL_MAX_DURATION_HINT_SECONDS=60
  VOICE_EVAL_HARD_MAX_DURATION_SECONDS=120
"""

from __future__ import annotations

import os
from typing import Any, Optional


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int, *, min_v: int = 1, max_v: int = 10_000) -> int:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return default
    return max(min_v, min(max_v, n))


# Defaults are intentionally tight for production polish (was 10/90/180).
VOICE_EVAL_MAX_DURATION_HINT_SECONDS = _env_int(
    "VOICE_EVAL_MAX_DURATION_HINT_SECONDS", 60, min_v=15, max_v=300
)
VOICE_EVAL_HARD_MAX_DURATION_SECONDS = _env_int(
    "VOICE_EVAL_HARD_MAX_DURATION_SECONDS", 120, min_v=30, max_v=300
)
# Ensure hard max is never below default hint
if VOICE_EVAL_HARD_MAX_DURATION_SECONDS < VOICE_EVAL_MAX_DURATION_HINT_SECONDS:
    VOICE_EVAL_HARD_MAX_DURATION_SECONDS = VOICE_EVAL_MAX_DURATION_HINT_SECONDS

VOICE_EVAL_MAX_SESSIONS_PER_ORG_HOUR = _env_int(
    "VOICE_EVAL_MAX_SESSIONS_PER_ORG_HOUR", 5, min_v=1, max_v=100
)
VOICE_EVAL_MAX_BATCH = 1  # no multi-scenario batch in one request — not env-tunable


def is_voice_eval_enabled() -> bool:
    """Process-level kill switch (VOICE_EVAL_ENABLED, default true)."""
    return _env_bool("VOICE_EVAL_ENABLED", True)


# Backward-compat name used in tests / imports
VOICE_EVAL_FEATURE_ENABLED = is_voice_eval_enabled()


class VoiceEvalGuardError(ValueError):
    """Raised when a voice-eval action is blocked by cost/safety policy."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def http_status_for_guard(code: str) -> int:
    if code == "rate_limited":
        return 429
    if code == "feature_disabled":
        return 403
    return 400


def clamp_max_duration_seconds(requested: Optional[int | float]) -> int:
    """Return a safe max-duration (seconds) for voice eval sessions."""
    if requested is None:
        return VOICE_EVAL_MAX_DURATION_HINT_SECONDS
    try:
        n = int(requested)
    except (TypeError, ValueError):
        return VOICE_EVAL_MAX_DURATION_HINT_SECONDS
    if n <= 0:
        return VOICE_EVAL_MAX_DURATION_HINT_SECONDS
    return min(n, VOICE_EVAL_HARD_MAX_DURATION_SECONDS)


def resolve_voice_eval_duration_cap(initial_context: dict | None) -> Optional[int]:
    """Read max_duration_hint from run initial_context (voice_eval or training_voice).

    Used by the pipeline to hard-cap call length for VEVAL/VTRAIN runs.
    """
    ctx = initial_context if isinstance(initial_context, dict) else {}
    for key in ("voice_eval", "training_voice"):
        block = ctx.get(key)
        if not isinstance(block, dict):
            continue
        raw = block.get("max_duration_hint_seconds")
        if raw is None:
            continue
        try:
            n = int(raw)
        except (TypeError, ValueError):
            continue
        if n > 0:
            return min(n, VOICE_EVAL_HARD_MAX_DURATION_SECONDS)
    return None


def check_voice_eval_allowed(
    *,
    recent_session_count: int = 0,
    batch_size: int = 1,
    feature_enabled: Optional[bool] = None,
) -> dict[str, Any]:
    """Validate that a new voice session may be created.

    Returns a guard payload on success; raises VoiceEvalGuardError otherwise.
    """
    enabled = is_voice_eval_enabled() if feature_enabled is None else bool(feature_enabled)
    if not enabled:
        raise VoiceEvalGuardError(
            "feature_disabled",
            "Voice eval is disabled (VOICE_EVAL_ENABLED=false). "
            "Use score-run on existing runs.",
        )
    if batch_size < 1:
        raise VoiceEvalGuardError("invalid_batch", "batch_size must be ≥ 1")
    if batch_size > VOICE_EVAL_MAX_BATCH:
        raise VoiceEvalGuardError(
            "batch_too_large",
            f"Voice eval batch limited to {VOICE_EVAL_MAX_BATCH} session(s); "
            f"requested {batch_size}. Use sampling, not full-suite voice runs.",
        )
    if recent_session_count >= VOICE_EVAL_MAX_SESSIONS_PER_ORG_HOUR:
        raise VoiceEvalGuardError(
            "rate_limited",
            f"Org voice-eval/training sessions capped at "
            f"{VOICE_EVAL_MAX_SESSIONS_PER_ORG_HOUR}/hour "
            f"(current hour: {recent_session_count}). Score existing runs instead.",
        )
    remaining = max(0, VOICE_EVAL_MAX_SESSIONS_PER_ORG_HOUR - recent_session_count - 1)
    return {
        "allowed": True,
        "enabled": True,
        "max_sessions_per_org_hour": VOICE_EVAL_MAX_SESSIONS_PER_ORG_HOUR,
        "recent_session_count": recent_session_count,
        "remaining_after": remaining,
        "max_duration_hint_seconds": VOICE_EVAL_MAX_DURATION_HINT_SECONDS,
        "hard_max_duration_seconds": VOICE_EVAL_HARD_MAX_DURATION_SECONDS,
        "max_batch": VOICE_EVAL_MAX_BATCH,
        "pipeline_duration_cap": True,
    }


def voice_eval_guard_payload(
    *,
    recent_session_count: int = 0,
    max_duration_seconds: Optional[int] = None,
    source: str = "voice_eval",
) -> dict[str, Any]:
    """Build annotations/tester metadata for a guarded voice session."""
    duration = clamp_max_duration_seconds(max_duration_seconds)
    return {
        "source": source,
        "modality": "voice",
        "max_duration_hint_seconds": duration,
        "rate_limit_per_hour": VOICE_EVAL_MAX_SESSIONS_PER_ORG_HOUR,
        "recent_session_count": recent_session_count,
        "batch_max": VOICE_EVAL_MAX_BATCH,
        "pipeline_duration_cap": True,
    }


def public_guard_config() -> dict[str, Any]:
    """Static config snapshot for health / status endpoints."""
    return {
        "enabled": is_voice_eval_enabled(),
        "max_sessions_per_org_hour": VOICE_EVAL_MAX_SESSIONS_PER_ORG_HOUR,
        "max_duration_hint_seconds": VOICE_EVAL_MAX_DURATION_HINT_SECONDS,
        "hard_max_duration_seconds": VOICE_EVAL_HARD_MAX_DURATION_SECONDS,
        "max_batch": VOICE_EVAL_MAX_BATCH,
        "pipeline_duration_cap": True,
        "env_keys": [
            "VOICE_EVAL_ENABLED",
            "VOICE_EVAL_MAX_SESSIONS_PER_ORG_HOUR",
            "VOICE_EVAL_MAX_DURATION_HINT_SECONDS",
            "VOICE_EVAL_HARD_MAX_DURATION_SECONDS",
        ],
    }
