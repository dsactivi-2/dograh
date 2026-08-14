"""Pure scoring helpers for shadow quiz + text drills + voice (P5/P6)."""

from __future__ import annotations

from typing import Any, Optional


def strip_quiz_answers(content: dict[str, Any] | None) -> dict[str, Any]:
    """Return module content safe for learners (no correct_option_ids)."""
    if not isinstance(content, dict):
        return {}
    out = dict(content)
    quiz = out.get("quiz")
    if isinstance(quiz, list):
        cleaned = []
        for q in quiz:
            if not isinstance(q, dict):
                continue
            cq = {k: v for k, v in q.items() if k != "correct_option_ids"}
            cleaned.append(cq)
        out["quiz"] = cleaned
    return out


def _norm_ids(ids: list[Any] | None) -> set[str]:
    if not ids:
        return set()
    return {str(x).strip() for x in ids if str(x).strip()}


def score_shadow_quiz(
    content: dict[str, Any] | None,
    answers: list[dict[str, Any]],
    *,
    pass_score: float = 70.0,
) -> dict[str, Any]:
    """Score shadow-mode quiz. Returns score 0–100, per-item results, passed."""
    quiz = []
    if isinstance(content, dict) and isinstance(content.get("quiz"), list):
        quiz = [q for q in content["quiz"] if isinstance(q, dict)]

    answer_map: dict[str, set[str]] = {}
    for a in answers or []:
        if not isinstance(a, dict):
            continue
        qid = str(a.get("question_id") or "").strip()
        if not qid:
            continue
        selected = a.get("selected_option_ids") or a.get("selected") or []
        if isinstance(selected, str):
            selected = [selected]
        answer_map[qid] = _norm_ids(list(selected))

    items: list[dict[str, Any]] = []
    correct_count = 0
    for q in quiz:
        qid = str(q.get("id") or "").strip()
        expected = _norm_ids(q.get("correct_option_ids") or [])
        selected = answer_map.get(qid, set())
        ok = bool(expected) and selected == expected
        if ok:
            correct_count += 1
        items.append(
            {
                "question_id": qid,
                "correct": ok,
                "selected": sorted(selected),
                "expected": sorted(expected),
                "explanation": str(q.get("explanation") or ""),
            }
        )

    total = len(quiz)
    score = round((correct_count / total * 100.0) if total else 0.0, 2)
    return {
        "mode": "shadow",
        "score": score,
        "passed": score >= float(pass_score),
        "correct_count": correct_count,
        "total_questions": total,
        "items": items,
        "pass_score": float(pass_score),
    }


def score_text_drill(
    *,
    eval_passed: bool,
    assertion_results: list[dict[str, Any]],
    disposition: Optional[str],
    success_codes: list[str] | None,
    pass_score: float = 70.0,
) -> dict[str, Any]:
    """Score text drill from eval harness output + disposition success set.

    Score composition (0–100):
    - 80% assertion pass rate (per-turn + final)
    - 20% disposition in success_codes (or full 20 if no success_codes configured
      and overall eval passed)
    """
    flat: list[dict[str, Any]] = []
    for a in assertion_results or []:
        if isinstance(a, dict):
            flat.append(a)

    total_assertions = len(flat)
    passed_assertions = sum(1 for a in flat if a.get("passed"))
    assertion_pct = (
        (passed_assertions / total_assertions * 100.0) if total_assertions else 0.0
    )

    codes = {str(c).strip().upper() for c in (success_codes or []) if str(c).strip()}
    disp = (disposition or "").strip().upper()
    disp_ok = False
    if codes:
        disp_ok = disp in codes
        disposition_score = 100.0 if disp_ok else 0.0
    else:
        # no success set configured — use overall eval pass as soft signal
        disp_ok = bool(eval_passed)
        disposition_score = 100.0 if eval_passed else 0.0

    if total_assertions == 0 and not codes:
        score = 100.0 if eval_passed else 0.0
    elif total_assertions == 0:
        score = disposition_score
    else:
        score = assertion_pct * 0.8 + disposition_score * 0.2

    score = round(score, 2)
    return {
        "mode": "text",
        "score": score,
        "passed": score >= float(pass_score),
        "assertion_pass_rate": round(assertion_pct, 2),
        "assertions_passed": passed_assertions,
        "assertions_total": total_assertions,
        "disposition": disposition,
        "disposition_success": disp_ok,
        "success_codes": sorted(codes),
        "eval_passed": bool(eval_passed),
        "pass_score": float(pass_score),
    }


def score_voice_drill(
    *,
    voice_score_payload: dict[str, Any],
    pass_score: float = 70.0,
) -> dict[str, Any]:
    """Adapt voice_score.score_voice_run output into a training attempt result.

    Reuses the numeric score from the voice scorer; stamps mode=voice.
    """
    payload = dict(voice_score_payload or {})
    score = float(payload.get("score") or 0.0)
    return {
        **payload,
        "mode": "voice",
        "score": round(score, 2),
        "passed": score >= float(pass_score),
        "pass_score": float(pass_score),
    }
