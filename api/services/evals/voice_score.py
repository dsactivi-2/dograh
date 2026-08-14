"""Score completed voice (or any) workflow runs from transcript + disposition + QA.

Pure helpers — no DB, no pipecat import (so unit tests run without the stack).
Used by /evals/voice/* and training voice complete.
"""

from __future__ import annotations

from typing import Any, Optional

from api.schemas.text_eval import AssertionResult, EvalAssertion
from api.services.evals.text_harness import evaluate_assertion
from api.services.outcomes.normalize import normalize_run_qa

# Mirror RealtimeFeedbackType values (avoid importing pipecat in pure tests)
_RTF_USER = "rtf-user-transcription"
_RTF_BOT = "rtf-bot-text"


def extract_rtf_events(logs: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(logs, dict):
        return []
    events = logs.get("realtime_feedback_events") or []
    if not isinstance(events, list):
        return []
    return [e for e in events if isinstance(e, dict)]


def generate_transcript_from_events(
    events: list[dict[str, Any]],
    *,
    include_end_timestamps: bool = False,
) -> str:
    """Same format as api.utils.transcript.generate_transcript_text (no pipecat)."""
    lines: list[str] = []
    for event in events:
        event_type = event.get("type")
        payload = event.get("payload") or {}
        if not isinstance(payload, dict):
            payload = {}

        if event_type == _RTF_USER and payload.get("final") is True:
            start = payload.get("timestamp") or event.get("timestamp") or ""
            end = payload.get("end_timestamp")
            if include_end_timestamps and end:
                ts = f"{start} -> {end}" if start else str(end)
            else:
                ts = start
            prefix = f"[{ts}] " if ts else ""
            lines.append(f"{prefix}user: {payload.get('text', '')}\n")
        elif event_type == _RTF_BOT:
            start = payload.get("timestamp") or event.get("timestamp") or ""
            end = payload.get("end_timestamp")
            if include_end_timestamps and end:
                ts = f"{start} -> {end}" if start else str(end)
            else:
                ts = start
            prefix = f"[{ts}] " if ts else ""
            lines.append(f"{prefix}assistant: {payload.get('text', '')}\n")
    return "".join(lines)


def extract_transcript(
    logs: dict[str, Any] | None,
    *,
    include_end_timestamps: bool = False,
) -> str:
    """Build transcript text from run.logs.realtime_feedback_events."""
    events = extract_rtf_events(logs)
    if not events:
        return ""
    return generate_transcript_from_events(
        events, include_end_timestamps=include_end_timestamps
    )


def extract_assistant_and_user_text(transcript: str) -> tuple[str, str]:
    """Split transcript lines into concatenated assistant / user blobs."""
    assistant_parts: list[str] = []
    user_parts: list[str] = []
    for raw in (transcript or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        body = line
        if line.startswith("["):
            close = line.find("]")
            if close != -1:
                body = line[close + 1 :].strip()
        body_lower = body.lower()
        if body_lower.startswith("user:"):
            user_parts.append(body.split(":", 1)[1].strip())
        elif body_lower.startswith("assistant:"):
            assistant_parts.append(body.split(":", 1)[1].strip())
    return "\n".join(assistant_parts), "\n".join(user_parts)


def extract_disposition(gathered: dict[str, Any] | None) -> Optional[str]:
    if not isinstance(gathered, dict):
        return None
    for key in (
        "mapped_call_disposition",
        "call_disposition",
        "disposition",
        "disposition_code",
    ):
        val = gathered.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return None


def run_assertions_on_transcript(
    assertions: list[EvalAssertion] | list[dict[str, Any]],
    *,
    transcript: str,
    gathered: dict[str, Any] | None,
) -> list[AssertionResult]:
    """Apply text-eval assertion types against full voice transcript + gathered."""
    assistant_text, _user = extract_assistant_and_user_text(transcript)
    combined = transcript or assistant_text
    g = gathered if isinstance(gathered, dict) else {}
    results: list[AssertionResult] = []
    for raw in assertions or []:
        if isinstance(raw, EvalAssertion):
            assertion = raw
        elif isinstance(raw, dict) and raw.get("type"):
            try:
                assertion = EvalAssertion(**raw)
            except Exception:
                results.append(
                    AssertionResult(
                        type=str(raw.get("type") or "invalid"),
                        passed=False,
                        detail="invalid assertion shape",
                    )
                )
                continue
        else:
            continue
        if assertion.type in (
            "disposition_equals",
            "gathered_key_exists",
            "gathered_key_equals",
        ):
            results.append(
                evaluate_assertion(
                    assertion, assistant_text=assistant_text, gathered=g
                )
            )
        else:
            results.append(
                evaluate_assertion(assertion, assistant_text=combined, gathered=g)
            )
    return results


def score_voice_run(
    *,
    run_id: int,
    workflow_id: Optional[int],
    mode: Optional[str],
    is_completed: bool,
    logs: dict[str, Any] | None,
    gathered_context: dict[str, Any] | None,
    annotations: dict[str, Any] | None,
    assertions: list[dict[str, Any]] | None = None,
    success_codes: list[str] | None = None,
    pass_score: float = 70.0,
    include_qa: bool = True,
) -> dict[str, Any]:
    """Score a completed (or partial) voice run.

    Score composition (0–100), aligned with text-drill:
    - 70% assertion pass rate (if any assertions)
    - 20% disposition ∈ success_codes (or soft if no codes)
    - 10% QA signal (avg node score or tag presence) when include_qa

    If no assertions configured: disposition 60% + QA 40% (or 100/0 if neither).
    """
    transcript = extract_transcript(logs)
    disposition = extract_disposition(gathered_context)
    assertion_results = run_assertions_on_transcript(
        assertions or [],
        transcript=transcript,
        gathered=gathered_context,
    )
    flat = [a.model_dump() if hasattr(a, "model_dump") else a for a in assertion_results]
    total_a = len(flat)
    passed_a = sum(1 for a in flat if a.get("passed"))
    assertion_pct = (passed_a / total_a * 100.0) if total_a else None

    codes = {str(c).strip().upper() for c in (success_codes or []) if str(c).strip()}
    disp = (disposition or "").strip().upper()
    if codes:
        disp_ok = disp in codes
        disposition_score = 100.0 if disp_ok else 0.0
    elif disposition:
        disp_ok = True
        disposition_score = 100.0
    else:
        disp_ok = False
        disposition_score = 0.0

    qa_payload: dict[str, Any] | None = None
    qa_score: Optional[float] = None
    qa_tags: list[str] = []
    if include_qa:
        qa = normalize_run_qa(run_id, annotations, workflow_id=workflow_id)
        qa_payload = qa.model_dump() if hasattr(qa, "model_dump") else None
        qa_tags = list(getattr(qa, "tags", None) or [])
        node_scores = [
            n.score
            for n in (getattr(qa, "nodes", None) or [])
            if getattr(n, "score", None) is not None
        ]
        if node_scores:
            qa_score = sum(node_scores) / len(node_scores)
            if qa_score <= 1.0:
                qa_score = qa_score * 100.0
        elif qa_tags:
            qa_score = 50.0
        else:
            qa_score = None

    if assertion_pct is not None and total_a > 0:
        if include_qa and qa_score is not None:
            score = assertion_pct * 0.7 + disposition_score * 0.2 + qa_score * 0.1
        else:
            score = assertion_pct * 0.8 + disposition_score * 0.2
    elif include_qa and qa_score is not None:
        score = disposition_score * 0.6 + qa_score * 0.4
    elif codes or disposition:
        score = disposition_score
    elif transcript.strip():
        score = 50.0
    else:
        score = 0.0

    score = round(float(score), 2)
    return {
        "mode": "voice",
        "run_id": run_id,
        "workflow_id": workflow_id,
        "run_mode": mode,
        "is_completed": bool(is_completed),
        "score": score,
        "passed": score >= float(pass_score),
        "pass_score": float(pass_score),
        "transcript": transcript,
        "transcript_chars": len(transcript),
        "has_transcript": bool(transcript.strip()),
        "disposition": disposition,
        "disposition_success": disp_ok,
        "success_codes": sorted(codes),
        "assertions_total": total_a,
        "assertions_passed": passed_a,
        "assertion_pass_rate": (
            round(assertion_pct, 2) if assertion_pct is not None else None
        ),
        "assertion_results": flat,
        "qa_score": round(qa_score, 2) if qa_score is not None else None,
        "qa_tags": qa_tags,
        "qa": qa_payload,
    }
