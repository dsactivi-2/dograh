"""Unit tests for disposition taxonomy normalize (no DB)."""

from api.services.disposition_taxonomy.service import (
    is_success_disposition,
    normalize_taxonomy,
    taxonomy_to_storage,
)


def test_legacy_list_shape():
    tax = normalize_taxonomy(["XFER", "DNC", "NO_ANSWER"])
    assert tax.disposition_codes == ["XFER", "DNC", "NO_ANSWER"]
    assert tax.success_codes == []
    assert "XFER" in tax.code_meta


def test_full_shape_and_success_subset():
    tax = normalize_taxonomy(
        {
            "disposition_codes": ["XFER", "DNC"],
            "success_codes": ["XFER", "BOGUS"],
            "code_meta": {"XFER": {"label": "Transfer", "category": "success"}},
        }
    )
    assert tax.success_codes == ["XFER"]  # BOGUS dropped
    assert tax.code_meta["XFER"].label == "Transfer"
    assert is_success_disposition(tax, "XFER") is True
    assert is_success_disposition(tax, "DNC") is False


def test_storage_roundtrip():
    tax = normalize_taxonomy(
        {
            "disposition_codes": ["A", "B"],
            "success_codes": ["A"],
            "code_meta": {"A": {"label": "Alpha", "category": "success", "description": ""}},
        }
    )
    stored = taxonomy_to_storage(tax)
    assert stored["disposition_codes"] == ["A", "B"]
    assert stored["success_codes"] == ["A"]
    again = normalize_taxonomy(stored)
    assert again.success_codes == ["A"]
    assert again.code_meta["A"].label == "Alpha"


def test_legacy_xfer_fallback():
    tax = normalize_taxonomy(["XFER"])
    # no success_codes set → XFER still treated as success for reports compat
    assert is_success_disposition(tax, "XFER") is True
