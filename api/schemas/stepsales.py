"""Pydantic schemas for the Stepsales sales API MVP."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

# Shared status vocabulary from the Stepsales API spec
LeadStatus = Literal[
    "new",
    "reached",
    "qualified",
    "proposal_pending",
    "second_call_scheduled",
    "negotiating",
    "verbally_closed",
    "payment_pending",
    "paid",
    "onboarding_pending",
    "fulfilled",
    "closed_lost",
    "no_fit",
]

CallOutcome = Literal[
    "no_answer",
    "voicemail",
    "not_interested",
    "callback",
    "qualified",
    "needs_offer",
    "second_call",
    "verbally_closed",
    "closed_lost",
    "no_fit",
]

InterestLevel = Literal["low", "medium", "high"]
UrgencyLevel = Literal["low", "medium", "high"]
FollowupType = Literal[
    "recap",
    "case_study",
    "pricing",
    "product_brief",
    "reminder",
    "callback_confirmation",
    "offer_recap",
]
PaymentMethod = Literal["direct_debit", "credit_card", "bank_transfer"]
PaymentStatus = Literal["pending", "paid", "failed", "canceled", "expired"]


class CallOutcomeRequest(BaseModel):
    lead_id: Optional[str] = None
    call_id: Optional[str] = None
    outcome: CallOutcome
    summary: str = Field(min_length=1, max_length=4000)
    interest_level: Optional[InterestLevel] = None
    objection_type: Optional[str] = Field(default=None, max_length=200)
    next_step: Optional[str] = Field(default=None, max_length=200)
    callback_date: Optional[date] = None


class CallOutcomeResponse(BaseModel):
    success: bool = True
    stored: bool = True
    outcome_id: str
    lead_id: Optional[str] = None


class QualifyLeadRequest(BaseModel):
    lead_id: Optional[str] = None
    company_name: str = Field(min_length=1, max_length=255)
    contact_name: Optional[str] = Field(default=None, max_length=255)
    role: Optional[str] = Field(default=None, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=64)
    active_hiring: bool = False
    roles_hiring_for: list[str] = Field(default_factory=list)
    urgency: Optional[UrgencyLevel] = None
    timeline: Optional[str] = Field(default=None, max_length=255)
    budget_signal: Optional[str] = Field(default=None, max_length=100)
    interest_level: Optional[InterestLevel] = None
    next_step: Optional[str] = Field(default=None, max_length=200)


class QualifyLeadResponse(BaseModel):
    success: bool = True
    lead_id: str
    score: int
    status: LeadStatus


class CreateOfferRequest(BaseModel):
    lead_id: str
    package_id: str
    list_price: Optional[float] = None
    discount_percent: float = Field(default=0, ge=0, le=10)
    discount_reason: Optional[str] = Field(default=None, max_length=500)
    valid_until: Optional[date] = None

    @field_validator("discount_percent")
    @classmethod
    def validate_discount(cls, value: float) -> float:
        if value > 10:
            raise ValueError("discount_percent must be <= 10")
        return value


class CreateOfferResponse(BaseModel):
    success: bool = True
    offer_id: str
    final_price: float
    list_price: float
    discount_percent: float
    package_id: str
    status: LeadStatus = "proposal_pending"


class SendFollowupRequest(BaseModel):
    lead_id: str
    email: EmailStr
    followup_type: FollowupType = "recap"
    template_id: str = "default_v1"
    next_step: Optional[str] = Field(default=None, max_length=200)
    subject: Optional[str] = Field(default=None, max_length=255)
    body_preview: Optional[str] = Field(default=None, max_length=4000)


class SendFollowupResponse(BaseModel):
    success: bool = True
    followup_id: str
    delivery_status: Literal["queued", "sent", "failed"] = "queued"


class ScheduleSecondCallRequest(BaseModel):
    lead_id: str
    email: Optional[EmailStr] = None
    preferred_date: date
    preferred_time: str = Field(min_length=4, max_length=16)
    timezone: str = "Europe/Berlin"
    notes: Optional[str] = Field(default=None, max_length=1000)


class ScheduleSecondCallResponse(BaseModel):
    success: bool = True
    appointment_id: str
    status: LeadStatus = "second_call_scheduled"
    scheduled_at: str


class SendPaymentLinkRequest(BaseModel):
    lead_id: str
    offer_id: str
    final_price: Optional[float] = None
    allowed_methods: list[PaymentMethod] = Field(
        default_factory=lambda: ["direct_debit", "credit_card", "bank_transfer"]
    )


class SendPaymentLinkResponse(BaseModel):
    success: bool = True
    payment_reference: str
    payment_link: str
    status: LeadStatus = "payment_pending"


class PaymentStatusResponse(BaseModel):
    success: bool = True
    payment_reference: str
    status: PaymentStatus
    amount: Optional[float] = None
    lead_id: Optional[str] = None
    offer_id: Optional[str] = None


class MarkPaymentReceivedRequest(BaseModel):
    lead_id: str
    payment_reference: str
    amount_received: Optional[float] = None
    payment_method: PaymentMethod = "credit_card"


class MarkPaymentReceivedResponse(BaseModel):
    success: bool = True
    status: LeadStatus = "paid"
    post_sale_triggered: bool = True


class PostSaleRequestDataRequest(BaseModel):
    lead_id: str
    email: EmailStr
    package_id: Optional[str] = None


class PostSaleRequestDataResponse(BaseModel):
    success: bool = True
    status: LeadStatus = "onboarding_pending"
    required_fields: list[str]
    request_id: str


class SearchJobsRequest(BaseModel):
    company_name: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)
    location: Optional[str] = None
    limit: int = Field(default=5, ge=1, le=20)


class SearchJobsResponse(BaseModel):
    success: bool = True
    results: list[dict]
    note: str = (
        "Optional enrichment only — never a hard dependency for the core sales path."
    )


class LeadResponse(BaseModel):
    lead_id: str
    organization_id: int
    company_name: str
    contact_name: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    active_hiring: bool
    roles_hiring_for: list[str]
    urgency: Optional[str] = None
    timeline: Optional[str] = None
    budget_signal: Optional[str] = None
    interest_level: Optional[str] = None
    next_step: Optional[str] = None
    score: int
    status: LeadStatus
    created_at: datetime
    updated_at: datetime


class PackageInfo(BaseModel):
    package_id: str
    name: str
    list_price: float
    description: str


class StepsalesHealthResponse(BaseModel):
    status: str = "ok"
    module: str = "stepsales"
    version: str = "0.1.0"
    packages: list[str]
