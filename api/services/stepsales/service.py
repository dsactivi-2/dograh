"""Business logic for the Stepsales sales API MVP."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import (
    StepsalesAppointmentModel,
    StepsalesCallOutcomeModel,
    StepsalesEventModel,
    StepsalesFollowupModel,
    StepsalesLeadModel,
    StepsalesOfferModel,
    StepsalesPaymentModel,
)
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
from api.services.stepsales.ids import (
    new_appointment_id,
    new_call_outcome_id,
    new_followup_id,
    new_lead_id,
    new_offer_id,
    new_payment_reference,
    new_request_id,
)
from api.services.stepsales.packages import (
    compute_final_price,
    get_package,
    list_packages,
)
from api.services.stepsales.scoring import score_lead, status_from_score

POST_PAYMENT_REQUIRED_FIELDS = [
    "job_title",
    "location",
    "employment_type",
    "description",
    "requirements",
    "benefits",
    "salary_if_available",
    "contact_details",
    "target_package_or_portals",
]


class StepsalesService:
    def __init__(self, session: AsyncSession, organization_id: int):
        self.session = session
        self.organization_id = organization_id

    async def _log_event(
        self, event_type: str, lead_id: Optional[str], payload: dict[str, Any]
    ) -> None:
        self.session.add(
            StepsalesEventModel(
                organization_id=self.organization_id,
                lead_id=lead_id,
                event_type=event_type,
                payload=payload,
            )
        )

    async def _get_lead(self, lead_id: str) -> StepsalesLeadModel:
        result = await self.session.execute(
            select(StepsalesLeadModel).where(
                StepsalesLeadModel.lead_id == lead_id,
                StepsalesLeadModel.organization_id == self.organization_id,
            )
        )
        lead = result.scalar_one_or_none()
        if not lead:
            raise HTTPException(status_code=404, detail=f"Lead not found: {lead_id}")
        return lead

    async def _set_lead_status(
        self, lead: StepsalesLeadModel, status: str, next_step: Optional[str] = None
    ) -> None:
        lead.status = status
        if next_step is not None:
            lead.next_step = next_step
        lead.updated_at = datetime.now(timezone.utc)

    async def log_call_outcome(self, body: CallOutcomeRequest) -> dict[str, Any]:
        if body.lead_id:
            await self._get_lead(body.lead_id)

        outcome_id = new_call_outcome_id()
        callback_dt = None
        if body.callback_date:
            callback_dt = datetime(
                body.callback_date.year,
                body.callback_date.month,
                body.callback_date.day,
                tzinfo=timezone.utc,
            )

        row = StepsalesCallOutcomeModel(
            outcome_id=outcome_id,
            organization_id=self.organization_id,
            lead_id=body.lead_id,
            call_id=body.call_id,
            outcome=body.outcome,
            summary=body.summary,
            interest_level=body.interest_level,
            objection_type=body.objection_type,
            next_step=body.next_step,
            callback_date=callback_dt,
        )
        self.session.add(row)

        if body.lead_id:
            lead = await self._get_lead(body.lead_id)
            if body.interest_level:
                lead.interest_level = body.interest_level
            if body.next_step:
                lead.next_step = body.next_step
            # Light status mapping from outcome codes
            outcome_status = {
                "qualified": "qualified",
                "needs_offer": "proposal_pending",
                "second_call": "second_call_scheduled",
                "verbally_closed": "verbally_closed",
                "closed_lost": "closed_lost",
                "no_fit": "no_fit",
                "not_interested": "closed_lost",
                "callback": "reached",
                "no_answer": "reached",
                "voicemail": "reached",
            }.get(body.outcome)
            if outcome_status:
                lead.status = outcome_status
            lead.updated_at = datetime.now(timezone.utc)

        await self._log_event(
            "call_outcome",
            body.lead_id,
            body.model_dump(mode="json"),
        )
        await self.session.commit()
        logger.info(
            "stepsales.call_outcome stored org={} outcome_id={} lead_id={}",
            self.organization_id,
            outcome_id,
            body.lead_id,
        )
        return {
            "success": True,
            "stored": True,
            "outcome_id": outcome_id,
            "lead_id": body.lead_id,
        }

    async def qualify_lead(self, body: QualifyLeadRequest) -> dict[str, Any]:
        payload = body.model_dump(mode="json")
        score = score_lead(payload)
        status = status_from_score(score)

        lead: Optional[StepsalesLeadModel] = None
        if body.lead_id:
            result = await self.session.execute(
                select(StepsalesLeadModel).where(
                    StepsalesLeadModel.lead_id == body.lead_id,
                    StepsalesLeadModel.organization_id == self.organization_id,
                )
            )
            lead = result.scalar_one_or_none()

        if lead is None:
            lead_id = body.lead_id or new_lead_id()
            lead = StepsalesLeadModel(
                lead_id=lead_id,
                organization_id=self.organization_id,
                company_name=body.company_name,
                contact_name=body.contact_name,
                role=body.role,
                email=str(body.email) if body.email else None,
                phone=body.phone,
                active_hiring=body.active_hiring,
                roles_hiring_for=body.roles_hiring_for or [],
                urgency=body.urgency,
                timeline=body.timeline,
                budget_signal=body.budget_signal,
                interest_level=body.interest_level,
                next_step=body.next_step,
                score=score,
                status=status,
            )
            self.session.add(lead)
        else:
            lead.company_name = body.company_name
            lead.contact_name = body.contact_name
            lead.role = body.role
            lead.email = str(body.email) if body.email else lead.email
            lead.phone = body.phone or lead.phone
            lead.active_hiring = body.active_hiring
            lead.roles_hiring_for = body.roles_hiring_for or []
            lead.urgency = body.urgency
            lead.timeline = body.timeline
            lead.budget_signal = body.budget_signal
            lead.interest_level = body.interest_level
            lead.next_step = body.next_step or lead.next_step
            lead.score = score
            # Do not downgrade a later pipeline status with a re-qualify
            if lead.status in {
                "new",
                "reached",
                "qualified",
            }:
                lead.status = status
            lead.updated_at = datetime.now(timezone.utc)

        await self._log_event(
            "qualify_lead",
            lead.lead_id,
            {**payload, "score": score, "status": lead.status},
        )
        await self.session.commit()
        await self.session.refresh(lead)
        logger.info(
            "stepsales.qualify_lead org={} lead_id={} score={} status={}",
            self.organization_id,
            lead.lead_id,
            score,
            lead.status,
        )
        return {
            "success": True,
            "lead_id": lead.lead_id,
            "score": score,
            "status": lead.status,
        }

    async def create_offer(self, body: CreateOfferRequest) -> dict[str, Any]:
        lead = await self._get_lead(body.lead_id)
        package = get_package(body.package_id)
        if not package:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown package_id '{body.package_id}'. "
                f"Known: {', '.join(p['package_id'] for p in list_packages())}",
            )

        list_price = (
            float(body.list_price)
            if body.list_price is not None
            else float(package["list_price"])
        )
        try:
            final_price = compute_final_price(list_price, body.discount_percent)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if body.discount_percent > 0 and not body.discount_reason:
            raise HTTPException(
                status_code=400,
                detail="discount_reason is required when discount_percent > 0",
            )

        offer_id = new_offer_id()
        valid_until_dt = None
        if body.valid_until:
            valid_until_dt = datetime(
                body.valid_until.year,
                body.valid_until.month,
                body.valid_until.day,
                tzinfo=timezone.utc,
            )
        else:
            valid_until_dt = datetime.now(timezone.utc) + timedelta(days=7)

        offer = StepsalesOfferModel(
            offer_id=offer_id,
            organization_id=self.organization_id,
            lead_id=lead.lead_id,
            package_id=body.package_id,
            list_price=list_price,
            discount_percent=body.discount_percent,
            discount_reason=body.discount_reason,
            final_price=final_price,
            valid_until=valid_until_dt,
            status="proposal_pending",
        )
        self.session.add(offer)
        await self._set_lead_status(lead, "proposal_pending", next_step="send_offer")
        await self._log_event(
            "create_offer",
            lead.lead_id,
            {
                "offer_id": offer_id,
                "package_id": body.package_id,
                "list_price": list_price,
                "discount_percent": body.discount_percent,
                "final_price": final_price,
            },
        )
        await self.session.commit()
        return {
            "success": True,
            "offer_id": offer_id,
            "final_price": final_price,
            "list_price": list_price,
            "discount_percent": body.discount_percent,
            "package_id": body.package_id,
            "status": "proposal_pending",
        }

    async def send_followup(self, body: SendFollowupRequest) -> dict[str, Any]:
        lead = await self._get_lead(body.lead_id)
        followup_id = new_followup_id()
        subject = body.subject or f"Stepsales Follow-up: {body.followup_type}"
        row = StepsalesFollowupModel(
            followup_id=followup_id,
            organization_id=self.organization_id,
            lead_id=lead.lead_id,
            email=str(body.email),
            followup_type=body.followup_type,
            template_id=body.template_id,
            next_step=body.next_step,
            subject=subject,
            body_preview=body.body_preview,
            delivery_status="queued",
        )
        self.session.add(row)
        if body.next_step:
            lead.next_step = body.next_step
            lead.updated_at = datetime.now(timezone.utc)
        await self._log_event(
            "send_followup",
            lead.lead_id,
            body.model_dump(mode="json") | {"followup_id": followup_id},
        )
        await self.session.commit()
        # MVP: mail provider is not wired yet — status stays queued, action is logged.
        return {
            "success": True,
            "followup_id": followup_id,
            "delivery_status": "queued",
        }

    async def schedule_second_call(
        self, body: ScheduleSecondCallRequest
    ) -> dict[str, Any]:
        lead = await self._get_lead(body.lead_id)
        appointment_id = new_appointment_id()
        row = StepsalesAppointmentModel(
            appointment_id=appointment_id,
            organization_id=self.organization_id,
            lead_id=lead.lead_id,
            email=str(body.email) if body.email else lead.email,
            preferred_date=body.preferred_date.isoformat(),
            preferred_time=body.preferred_time,
            timezone=body.timezone,
            notes=body.notes,
            status="second_call_scheduled",
        )
        self.session.add(row)
        await self._set_lead_status(
            lead, "second_call_scheduled", next_step="second_call"
        )
        scheduled_at = f"{body.preferred_date.isoformat()}T{body.preferred_time}"
        await self._log_event(
            "schedule_second_call",
            lead.lead_id,
            body.model_dump(mode="json") | {"appointment_id": appointment_id},
        )
        await self.session.commit()
        return {
            "success": True,
            "appointment_id": appointment_id,
            "status": "second_call_scheduled",
            "scheduled_at": scheduled_at,
        }

    async def send_payment_link(self, body: SendPaymentLinkRequest) -> dict[str, Any]:
        lead = await self._get_lead(body.lead_id)
        offer_result = await self.session.execute(
            select(StepsalesOfferModel).where(
                StepsalesOfferModel.offer_id == body.offer_id,
                StepsalesOfferModel.organization_id == self.organization_id,
            )
        )
        offer = offer_result.scalar_one_or_none()
        if not offer:
            raise HTTPException(
                status_code=404, detail=f"Offer not found: {body.offer_id}"
            )
        if offer.lead_id != lead.lead_id:
            raise HTTPException(
                status_code=400, detail="offer_id does not belong to lead_id"
            )

        amount = (
            float(body.final_price)
            if body.final_price is not None
            else float(offer.final_price)
        )
        payment_reference = new_payment_reference()
        payment_link = f"https://payments.stepsales.local/pay/{payment_reference}"
        row = StepsalesPaymentModel(
            payment_reference=payment_reference,
            organization_id=self.organization_id,
            lead_id=lead.lead_id,
            offer_id=offer.offer_id,
            amount=amount,
            allowed_methods=body.allowed_methods,
            payment_link=payment_link,
            status="pending",
        )
        self.session.add(row)
        await self._set_lead_status(
            lead, "payment_pending", next_step="await_payment"
        )
        offer.status = "payment_pending"
        await self._log_event(
            "send_payment_link",
            lead.lead_id,
            {
                "payment_reference": payment_reference,
                "offer_id": offer.offer_id,
                "amount": amount,
            },
        )
        await self.session.commit()
        return {
            "success": True,
            "payment_reference": payment_reference,
            "payment_link": payment_link,
            "status": "payment_pending",
        }

    async def check_payment_status(self, payment_reference: str) -> dict[str, Any]:
        result = await self.session.execute(
            select(StepsalesPaymentModel).where(
                StepsalesPaymentModel.payment_reference == payment_reference,
                StepsalesPaymentModel.organization_id == self.organization_id,
            )
        )
        payment = result.scalar_one_or_none()
        if not payment:
            raise HTTPException(
                status_code=404,
                detail=f"Payment not found: {payment_reference}",
            )
        return {
            "success": True,
            "payment_reference": payment.payment_reference,
            "status": payment.status,
            "amount": payment.amount,
            "lead_id": payment.lead_id,
            "offer_id": payment.offer_id,
        }

    async def mark_payment_received(
        self, body: MarkPaymentReceivedRequest
    ) -> dict[str, Any]:
        lead = await self._get_lead(body.lead_id)
        result = await self.session.execute(
            select(StepsalesPaymentModel).where(
                StepsalesPaymentModel.payment_reference == body.payment_reference,
                StepsalesPaymentModel.organization_id == self.organization_id,
            )
        )
        payment = result.scalar_one_or_none()
        if not payment:
            raise HTTPException(
                status_code=404,
                detail=f"Payment not found: {body.payment_reference}",
            )
        if payment.lead_id != lead.lead_id:
            raise HTTPException(
                status_code=400, detail="payment_reference does not belong to lead_id"
            )

        payment.status = "paid"
        payment.payment_method = body.payment_method
        payment.post_sale_triggered = True
        if body.amount_received is not None:
            payment.amount = float(body.amount_received)
        payment.updated_at = datetime.now(timezone.utc)

        offer_result = await self.session.execute(
            select(StepsalesOfferModel).where(
                StepsalesOfferModel.offer_id == payment.offer_id,
                StepsalesOfferModel.organization_id == self.organization_id,
            )
        )
        offer = offer_result.scalar_one_or_none()
        if offer:
            offer.status = "paid"

        await self._set_lead_status(lead, "paid", next_step="collect_ad_data")
        await self._log_event(
            "mark_payment_received",
            lead.lead_id,
            body.model_dump(mode="json"),
        )
        await self.session.commit()
        return {
            "success": True,
            "status": "paid",
            "post_sale_triggered": True,
        }

    async def send_post_payment_request(
        self, body: PostSaleRequestDataRequest
    ) -> dict[str, Any]:
        lead = await self._get_lead(body.lead_id)
        request_id = new_request_id()
        followup_id = new_followup_id()
        self.session.add(
            StepsalesFollowupModel(
                followup_id=followup_id,
                organization_id=self.organization_id,
                lead_id=lead.lead_id,
                email=str(body.email),
                followup_type="post_payment_data_request",
                template_id="post_payment_request_v1",
                next_step="collect_ad_data",
                subject="Bitte senden Sie die Daten für Ihre Stellenanzeige",
                body_preview=(
                    "Bitte liefern Sie: " + ", ".join(POST_PAYMENT_REQUIRED_FIELDS)
                ),
                delivery_status="queued",
            )
        )
        await self._set_lead_status(
            lead, "onboarding_pending", next_step="collect_ad_data"
        )
        await self._log_event(
            "send_post_payment_request",
            lead.lead_id,
            {
                "request_id": request_id,
                "package_id": body.package_id,
                "required_fields": POST_PAYMENT_REQUIRED_FIELDS,
            },
        )
        await self.session.commit()
        return {
            "success": True,
            "status": "onboarding_pending",
            "required_fields": POST_PAYMENT_REQUIRED_FIELDS,
            "request_id": request_id,
        }

    async def search_jobs(self, body: SearchJobsRequest) -> dict[str, Any]:
        # Optional enrichment only — returns stable mock context so workflows
        # never hard-depend on live portal scrapers.
        company = body.company_name or "Unbekanntes Unternehmen"
        keywords = body.keywords or ["allgemein"]
        results = []
        for i, kw in enumerate(keywords[: body.limit]):
            results.append(
                {
                    "title": f"{kw.title()} (offen)",
                    "company": company,
                    "location": body.location or "Deutschland",
                    "source": "stepsales_mock",
                    "posted_within_days": 3 + i,
                    "relevance": "context_only",
                }
            )
        await self._log_event(
            "search_jobs",
            None,
            body.model_dump(mode="json") | {"result_count": len(results)},
        )
        await self.session.commit()
        return {
            "success": True,
            "results": results,
            "note": (
                "Optional enrichment only — never a hard dependency for the core "
                "sales path."
            ),
        }

    async def list_leads(self, limit: int = 50) -> list[StepsalesLeadModel]:
        result = await self.session.execute(
            select(StepsalesLeadModel)
            .where(StepsalesLeadModel.organization_id == self.organization_id)
            .order_by(StepsalesLeadModel.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_lead(self, lead_id: str) -> StepsalesLeadModel:
        return await self._get_lead(lead_id)
