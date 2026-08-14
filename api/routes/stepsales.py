"""REST routes for the Stepsales sales API MVP.

Mounted under /api/v1/stepsales/*
Auth: Dograh user or API key via get_user (X-API-Key / Authorization).
Org scope: user.selected_organization_id
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from api.db import db_client
from api.db.models import UserModel
from api.schemas.stepsales import (
    CallOutcomeRequest,
    CallOutcomeResponse,
    CreateOfferRequest,
    CreateOfferResponse,
    LeadResponse,
    MarkPaymentReceivedRequest,
    MarkPaymentReceivedResponse,
    PackageInfo,
    PaymentStatusResponse,
    PostSaleRequestDataRequest,
    PostSaleRequestDataResponse,
    QualifyLeadRequest,
    QualifyLeadResponse,
    ScheduleSecondCallRequest,
    ScheduleSecondCallResponse,
    SearchJobsRequest,
    SearchJobsResponse,
    SendFollowupRequest,
    SendFollowupResponse,
    SendPaymentLinkRequest,
    SendPaymentLinkResponse,
    StepsalesHealthResponse,
)
from api.services.auth.depends import get_user
from api.services.stepsales.packages import list_packages

router = APIRouter(prefix="/stepsales", tags=["stepsales"])


def _require_org(user: UserModel) -> int:
    org_id = user.selected_organization_id
    if not org_id:
        raise HTTPException(
            status_code=400,
            detail="No organization selected for the authenticated user",
        )
    return int(org_id)


def _lead_to_response(lead) -> LeadResponse:
    return LeadResponse(
        lead_id=lead.lead_id,
        organization_id=lead.organization_id,
        company_name=lead.company_name,
        contact_name=lead.contact_name,
        role=lead.role,
        email=lead.email,
        phone=lead.phone,
        active_hiring=bool(lead.active_hiring),
        roles_hiring_for=lead.roles_hiring_for or [],
        urgency=lead.urgency,
        timeline=lead.timeline,
        budget_signal=lead.budget_signal,
        interest_level=lead.interest_level,
        next_step=lead.next_step,
        score=int(lead.score or 0),
        status=lead.status,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
    )


@router.get("/health", response_model=StepsalesHealthResponse)
async def stepsales_health() -> StepsalesHealthResponse:
    packages = [p["package_id"] for p in list_packages()]
    return StepsalesHealthResponse(packages=packages)


@router.get("/packages", response_model=List[PackageInfo])
async def get_packages(
    user: UserModel = Depends(get_user),
) -> List[PackageInfo]:
    _require_org(user)
    return [PackageInfo(**p) for p in list_packages()]


@router.post("/calls/outcome", response_model=CallOutcomeResponse)
async def log_call_outcome(
    body: CallOutcomeRequest,
    user: UserModel = Depends(get_user),
) -> CallOutcomeResponse:
    result = await db_client.log_call_outcome(_require_org(user), body)
    return CallOutcomeResponse(**result)


@router.post("/leads/qualify", response_model=QualifyLeadResponse)
async def qualify_lead(
    body: QualifyLeadRequest,
    user: UserModel = Depends(get_user),
) -> QualifyLeadResponse:
    result = await db_client.qualify_lead(_require_org(user), body)
    return QualifyLeadResponse(**result)


@router.get("/leads", response_model=List[LeadResponse])
async def list_leads(
    limit: int = 50,
    user: UserModel = Depends(get_user),
) -> List[LeadResponse]:
    leads = await db_client.list_leads(
        _require_org(user), limit=min(max(limit, 1), 200)
    )
    return [_lead_to_response(lead) for lead in leads]


@router.get("/leads/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: str,
    user: UserModel = Depends(get_user),
) -> LeadResponse:
    lead = await db_client.get_lead(_require_org(user), lead_id)
    return _lead_to_response(lead)


@router.post("/offers/create", response_model=CreateOfferResponse)
async def create_offer(
    body: CreateOfferRequest,
    user: UserModel = Depends(get_user),
) -> CreateOfferResponse:
    result = await db_client.create_offer(_require_org(user), body)
    return CreateOfferResponse(**result)


@router.post("/followups/send", response_model=SendFollowupResponse)
async def send_followup(
    body: SendFollowupRequest,
    user: UserModel = Depends(get_user),
) -> SendFollowupResponse:
    result = await db_client.send_followup(_require_org(user), body)
    return SendFollowupResponse(**result)


@router.post("/appointments/second-call", response_model=ScheduleSecondCallResponse)
async def schedule_second_call(
    body: ScheduleSecondCallRequest,
    user: UserModel = Depends(get_user),
) -> ScheduleSecondCallResponse:
    result = await db_client.schedule_second_call(_require_org(user), body)
    return ScheduleSecondCallResponse(**result)


@router.post("/payments/link", response_model=SendPaymentLinkResponse)
async def send_payment_link(
    body: SendPaymentLinkRequest,
    user: UserModel = Depends(get_user),
) -> SendPaymentLinkResponse:
    result = await db_client.send_payment_link(_require_org(user), body)
    return SendPaymentLinkResponse(**result)


@router.get(
    "/payments/status/{payment_reference}",
    response_model=PaymentStatusResponse,
)
async def check_payment_status(
    payment_reference: str,
    user: UserModel = Depends(get_user),
) -> PaymentStatusResponse:
    result = await db_client.check_payment_status(
        _require_org(user), payment_reference
    )
    return PaymentStatusResponse(**result)


@router.post("/payments/mark-received", response_model=MarkPaymentReceivedResponse)
async def mark_payment_received(
    body: MarkPaymentReceivedRequest,
    user: UserModel = Depends(get_user),
) -> MarkPaymentReceivedResponse:
    result = await db_client.mark_payment_received(_require_org(user), body)
    return MarkPaymentReceivedResponse(**result)


@router.post("/post-sale/request-data", response_model=PostSaleRequestDataResponse)
async def send_post_payment_request(
    body: PostSaleRequestDataRequest,
    user: UserModel = Depends(get_user),
) -> PostSaleRequestDataResponse:
    result = await db_client.send_post_payment_request(_require_org(user), body)
    return PostSaleRequestDataResponse(**result)


@router.post("/jobs/search", response_model=SearchJobsResponse)
async def search_jobs(
    body: SearchJobsRequest,
    user: UserModel = Depends(get_user),
) -> SearchJobsResponse:
    result = await db_client.search_jobs(_require_org(user), body)
    return SearchJobsResponse(**result)


logger.info("stepsales routes loaded")
