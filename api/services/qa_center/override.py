"""Manual QA override stored on workflow_run.annotations (audit-ready)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from api.schemas.qa_center import QaManualOverridePayload, QaManualOverrideRecord

OVERRIDE_KEY = "qa_manual_override"
AUDIT_KEY = "qa_override_audit"
MAX_AUDIT_ENTRIES = 50


def read_override(annotations: dict[str, Any] | None) -> Optional[QaManualOverrideRecord]:
    ann = annotations if isinstance(annotations, dict) else {}
    raw = ann.get(OVERRIDE_KEY)
    if not isinstance(raw, dict):
        return None
    try:
        return QaManualOverrideRecord.model_validate(raw)
    except Exception:
        return None


def read_audit_history(annotations: dict[str, Any] | None) -> list[dict[str, Any]]:
    ann = annotations if isinstance(annotations, dict) else {}
    hist = ann.get(AUDIT_KEY)
    if not isinstance(hist, list):
        return []
    return [h for h in hist if isinstance(h, dict)]


def apply_manual_override(
    annotations: dict[str, Any] | None,
    payload: QaManualOverridePayload,
    *,
    reviewer_user_id: int,
    reviewer_email: Optional[str] = None,
) -> dict[str, Any]:
    """Merge a new override into annotations with previous snapshot + audit list.

    Returns a **patch** suitable for ``db_client.update_workflow_run(annotations=…)``
    (shallow-merged into existing annotations by the DB client).
    """
    existing = dict(annotations or {})
    previous_raw = existing.get(OVERRIDE_KEY)
    previous_snapshot: Optional[dict[str, Any]] = None
    if isinstance(previous_raw, dict):
        # Drop nested previous to avoid unbounded nesting depth
        previous_snapshot = {
            k: v for k, v in previous_raw.items() if k != "previous"
        }

    now = datetime.now(timezone.utc).isoformat()
    record = QaManualOverrideRecord(
        schema_version=1,
        overall_score=payload.overall_score,
        sentiment=(payload.sentiment.strip().lower() if payload.sentiment else None),
        tags=[str(t).strip() for t in payload.tags if str(t).strip()],
        summary=payload.summary or "",
        notes=payload.notes or "",
        compliance_flags=dict(payload.compliance_flags or {}),
        reviewer_user_id=reviewer_user_id,
        reviewer_email=reviewer_email,
        created_at=now,
        previous=previous_snapshot,
    )
    record_dict = record.model_dump()

    audit = list(read_audit_history(existing))
    audit.insert(
        0,
        {
            "at": now,
            "reviewer_user_id": reviewer_user_id,
            "reviewer_email": reviewer_email,
            "override": {k: v for k, v in record_dict.items() if k != "previous"},
        },
    )
    audit = audit[:MAX_AUDIT_ENTRIES]

    return {
        OVERRIDE_KEY: record_dict,
        AUDIT_KEY: audit,
    }
