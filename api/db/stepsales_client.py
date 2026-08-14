"""DB client facade for Stepsales sales operations."""

from __future__ import annotations

from typing import Any

from api.db.base_client import BaseDBClient
from api.schemas.stepsales import (
    CallOutcomeRequest,
    CreateOfferRequest,
    MarkPaymentReceivedRequest,
    PostSaleRequestDataRequest,
    QualifyLeadRequest,
    ScheduleSecondCallRequest,
    SearchJobsRequest,
    SendFollowupRequest,
    SendPaymentLinkRequest,
)
from api.services.stepsales.service import StepsalesService


class StepsalesClient(BaseDBClient):
    async def log_call_outcome(
        self, organization_id: int, body: CallOutcomeRequest
    ) -> dict[str, Any]:
        async with self.async_session() as session:
            svc = StepsalesService(session, organization_id)
            return await svc.log_call_outcome(body)

    async def qualify_lead(
        self, organization_id: int, body: QualifyLeadRequest
    ) -> dict[str, Any]:
        async with self.async_session() as session:
            svc = StepsalesService(session, organization_id)
            return await svc.qualify_lead(body)

    async def create_offer(
        self, organization_id: int, body: CreateOfferRequest
    ) -> dict[str, Any]:
        async with self.async_session() as session:
            svc = StepsalesService(session, organization_id)
            return await svc.create_offer(body)

    async def send_followup(
        self, organization_id: int, body: SendFollowupRequest
    ) -> dict[str, Any]:
        async with self.async_session() as session:
            svc = StepsalesService(session, organization_id)
            return await svc.send_followup(body)

    async def schedule_second_call(
        self, organization_id: int, body: ScheduleSecondCallRequest
    ) -> dict[str, Any]:
        async with self.async_session() as session:
            svc = StepsalesService(session, organization_id)
            return await svc.schedule_second_call(body)

    async def send_payment_link(
        self, organization_id: int, body: SendPaymentLinkRequest
    ) -> dict[str, Any]:
        async with self.async_session() as session:
            svc = StepsalesService(session, organization_id)
            return await svc.send_payment_link(body)

    async def check_payment_status(
        self, organization_id: int, payment_reference: str
    ) -> dict[str, Any]:
        async with self.async_session() as session:
            svc = StepsalesService(session, organization_id)
            return await svc.check_payment_status(payment_reference)

    async def mark_payment_received(
        self, organization_id: int, body: MarkPaymentReceivedRequest
    ) -> dict[str, Any]:
        async with self.async_session() as session:
            svc = StepsalesService(session, organization_id)
            return await svc.mark_payment_received(body)

    async def send_post_payment_request(
        self, organization_id: int, body: PostSaleRequestDataRequest
    ) -> dict[str, Any]:
        async with self.async_session() as session:
            svc = StepsalesService(session, organization_id)
            return await svc.send_post_payment_request(body)

    async def search_jobs(
        self, organization_id: int, body: SearchJobsRequest
    ) -> dict[str, Any]:
        async with self.async_session() as session:
            svc = StepsalesService(session, organization_id)
            return await svc.search_jobs(body)

    async def list_leads(self, organization_id: int, limit: int = 50):
        async with self.async_session() as session:
            svc = StepsalesService(session, organization_id)
            return await svc.list_leads(limit=limit)

    async def get_lead(self, organization_id: int, lead_id: str):
        async with self.async_session() as session:
            svc = StepsalesService(session, organization_id)
            return await svc.get_lead(lead_id)
