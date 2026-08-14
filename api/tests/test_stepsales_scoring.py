"""Unit tests for Stepsales scoring, packages, and schema validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from api.schemas.stepsales import (
    CreateOfferRequest,
    QualifyLeadRequest,
    CallOutcomeRequest,
)
from api.services.stepsales.packages import (
    compute_final_price,
    get_package,
    list_packages,
)
from api.services.stepsales.scoring import score_lead, status_from_score


def test_package_catalog_contains_core_packages():
    packages = {p["package_id"] for p in list_packages()}
    assert packages == {"MULTI_S", "MULTI_M", "MULTI_L"}
    multi_m = get_package("MULTI_M")
    assert multi_m is not None
    assert multi_m["list_price"] == 1490.0


def test_compute_final_price_with_max_discount():
    assert compute_final_price(1490, 10) == 1341.0
    assert compute_final_price(1000, 0) == 1000.0


def test_compute_final_price_rejects_over_discount():
    with pytest.raises(ValueError):
        compute_final_price(1000, 11)


def test_score_lead_high_quality():
    score = score_lead(
        {
            "active_hiring": True,
            "urgency": "high",
            "interest_level": "high",
            "email": "max@techcorp.de",
            "phone": "+49301234567",
            "roles_hiring_for": ["Software Engineer", "Sales Manager", "HR"],
            "budget_signal": "open",
            "timeline": "2 weeks",
        }
    )
    assert score >= 70
    assert status_from_score(score) == "qualified"


def test_score_lead_low_quality():
    score = score_lead(
        {
            "active_hiring": False,
            "urgency": "low",
            "interest_level": "low",
        }
    )
    assert score < 40
    assert status_from_score(score) == "new"


def test_qualify_lead_request_validation():
    req = QualifyLeadRequest(
        company_name="TechCorp GmbH",
        contact_name="Max Müller",
        email="max@techcorp.de",
        active_hiring=True,
        roles_hiring_for=["Software Engineer"],
        urgency="high",
        interest_level="high",
        next_step="send_offer",
    )
    assert req.company_name == "TechCorp GmbH"


def test_create_offer_rejects_discount_over_10():
    with pytest.raises(ValidationError):
        CreateOfferRequest(
            lead_id="LEAD-001",
            package_id="MULTI_M",
            discount_percent=15,
        )


def test_call_outcome_request_accepts_spec_payload():
    req = CallOutcomeRequest(
        lead_id="LEAD-001",
        call_id="CALL-001",
        outcome="qualified",
        summary="Active hiring for 3 roles, wants an offer.",
        interest_level="high",
        objection_type="price",
        next_step="send_offer",
        callback_date=None,
    )
    assert req.outcome == "qualified"
