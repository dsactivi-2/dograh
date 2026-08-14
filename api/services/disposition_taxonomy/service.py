"""Normalize and store disposition taxonomy on workflows."""

from __future__ import annotations

from typing import Any

from api.schemas.disposition_taxonomy import DispositionCodeMeta, DispositionTaxonomy


def normalize_taxonomy(raw: Any) -> DispositionTaxonomy:
    """Accept legacy list/dict shapes and return DispositionTaxonomy."""
    if raw is None:
        return DispositionTaxonomy()
    if isinstance(raw, list):
        codes = [str(x).strip() for x in raw if str(x).strip()]
        meta = {
            c: DispositionCodeMeta(label=c, category="other") for c in codes
        }
        return DispositionTaxonomy(disposition_codes=codes, code_meta=meta)
    if not isinstance(raw, dict):
        return DispositionTaxonomy()

    codes = raw.get("disposition_codes") or raw.get("codes") or []
    if isinstance(codes, str):
        codes = [codes]
    codes = [str(c).strip() for c in codes if str(c).strip()]

    success = raw.get("success_codes") or raw.get("success_set") or []
    if isinstance(success, str):
        success = [success]
    success = [str(c).strip() for c in success if str(c).strip()]
    # success codes must be subset of disposition_codes when codes exist
    if codes:
        success = [c for c in success if c in codes]

    meta_raw = raw.get("code_meta") or {}
    meta: dict[str, DispositionCodeMeta] = {}
    if isinstance(meta_raw, dict):
        for k, v in meta_raw.items():
            key = str(k).strip()
            if not key:
                continue
            if isinstance(v, DispositionCodeMeta):
                meta[key] = v
            elif isinstance(v, dict):
                try:
                    meta[key] = DispositionCodeMeta(**v)
                except Exception:
                    meta[key] = DispositionCodeMeta(label=str(v.get("label") or key))
            elif isinstance(v, str):
                meta[key] = DispositionCodeMeta(label=v)

    # ensure meta keys for all codes
    for c in codes:
        if c not in meta:
            cat = "success" if c in success else "other"
            meta[c] = DispositionCodeMeta(label=c, category=cat)

    return DispositionTaxonomy(
        disposition_codes=codes,
        success_codes=success,
        code_meta=meta,
    )


def taxonomy_to_storage(tax: DispositionTaxonomy) -> dict[str, Any]:
    """Serialize taxonomy for JSON column (keeps disposition_codes key)."""
    return {
        "disposition_codes": list(tax.disposition_codes),
        "success_codes": list(tax.success_codes),
        "code_meta": {
            k: v.model_dump() if hasattr(v, "model_dump") else dict(v)
            for k, v in tax.code_meta.items()
        },
    }


def is_success_disposition(tax: DispositionTaxonomy, code: str | None) -> bool:
    if not code:
        return False
    if tax.success_codes:
        return code in tax.success_codes
    # fallback legacy: XFER counted as success in daily reports
    return code == "XFER"
