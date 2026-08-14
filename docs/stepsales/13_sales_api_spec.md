# Stepsales Sales API Specification

## Purpose

This document defines the recommended real backend endpoints behind the Stepsales workflow templates.

## API Design Principles

- JSON in / JSON out
- explicit validation
- stable status values
- idempotent behavior where possible
- every action logged

## 1. `POST /api/v1/stepsales/calls/outcome`

### Purpose

Persist structured call outcome.

### Request body

```json
{
  "lead_id": "LEAD-001",
  "call_id": "CALL-001",
  "outcome": "qualified",
  "summary": "Active hiring for 3 roles, wants an offer.",
  "interest_level": "high",
  "objection_type": "price",
  "next_step": "send_offer",
  "callback_date": null
}
```

### Response

```json
{
  "success": true,
  "stored": true
}
```

## 2. `POST /api/v1/stepsales/leads/qualify`

### Purpose

Create or update qualified lead.

### Request body

```json
{
  "company_name": "TechCorp GmbH",
  "contact_name": "Max Müller",
  "role": "HR Manager",
  "email": "max@techcorp.de",
  "phone": "+49301234567",
  "active_hiring": true,
  "roles_hiring_for": ["Software Engineer", "Sales Manager"],
  "urgency": "high",
  "timeline": "2 weeks",
  "budget_signal": "open",
  "interest_level": "high",
  "next_step": "send_offer"
}
```

### Response

```json
{
  "success": true,
  "lead_id": "LEAD-001",
  "score": 82,
  "status": "qualified"
}
```

## 3. `POST /api/v1/stepsales/offers/create`

### Purpose

Create formal commercial offer.

### Request body

```json
{
  "lead_id": "LEAD-001",
  "package_id": "MULTI_M",
  "list_price": 1490,
  "discount_percent": 10,
  "discount_reason": "close_this_week",
  "valid_until": "2026-05-20"
}
```

### Validation rules

- `discount_percent <= 10`
- package must exist
- final price must be computed server-side

### Response

```json
{
  "success": true,
  "offer_id": "OFF-001",
  "final_price": 1341,
  "status": "proposal_pending"
}
```

## 4. `POST /api/v1/stepsales/followups/send`

### Purpose

Send recap, material, offer or reminder.

### Request body

```json
{
  "lead_id": "LEAD-001",
  "email": "max@techcorp.de",
  "followup_type": "offer_recap",
  "template_id": "offer_recap_v1",
  "next_step": "review_offer"
}
```

### Response

```json
{
  "success": true,
  "delivery_status": "queued"
}
```

## 5. `POST /api/v1/stepsales/appointments/second-call`

### Purpose

Book second sales call.

### Request body

```json
{
  "lead_id": "LEAD-001",
  "email": "max@techcorp.de",
  "preferred_date": "2026-05-14",
  "preferred_time": "10:30",
  "timezone": "Europe/Berlin"
}
```

### Response

```json
{
  "success": true,
  "appointment_id": "APT-001",
  "status": "second_call_scheduled"
}
```

## 6. `POST /api/v1/stepsales/payments/link`

### Purpose

Create and send payment link.

### Request body

```json
{
  "lead_id": "LEAD-001",
  "offer_id": "OFF-001",
  "final_price": 1341,
  "allowed_methods": ["direct_debit", "credit_card", "bank_transfer"]
}
```

### Response

```json
{
  "success": true,
  "payment_reference": "PAY-001",
  "payment_link": "https://payments.example.com/pay/PAY-001",
  "status": "payment_pending"
}
```

## 7. `GET /api/v1/stepsales/payments/status/{payment_reference}`

### Purpose

Return normalized payment status.

### Response

```json
{
  "success": true,
  "payment_reference": "PAY-001",
  "status": "paid"
}
```

## 8. `POST /api/v1/stepsales/payments/mark-received`

### Purpose

Finalize payment success internally.

### Request body

```json
{
  "lead_id": "LEAD-001",
  "payment_reference": "PAY-001",
  "amount_received": 1341,
  "payment_method": "credit_card"
}
```

### Response

```json
{
  "success": true,
  "status": "paid",
  "post_sale_triggered": true
}
```

## 9. `POST /api/v1/stepsales/post-sale/request-data`

### Purpose

Send all required ad-publication data request after payment.

### Request body

```json
{
  "lead_id": "LEAD-001",
  "email": "max@techcorp.de",
  "package_id": "MULTI_M"
}
```

### Response

```json
{
  "success": true,
  "status": "onboarding_pending"
}
```

## 10. Optional `POST /api/v1/stepsales/jobs/search`

### Purpose

Context enrichment from job-source activity.

### Rule

This endpoint is optional and should never be the single point of failure for the core sales workflow.

## Status Vocabulary

Recommended shared states:

- `new`
- `reached`
- `qualified`
- `proposal_pending`
- `second_call_scheduled`
- `negotiating`
- `verbally_closed`
- `payment_pending`
- `paid`
- `onboarding_pending`
- `fulfilled`
- `closed_lost`
- `no_fit`

## Tool-to-Endpoint Mapping

- `log_call_outcome` -> `POST /api/v1/stepsales/calls/outcome`
- `qualify_lead` -> `POST /api/v1/stepsales/leads/qualify`
- `create_offer` -> `POST /api/v1/stepsales/offers/create`
- `send_followup` -> `POST /api/v1/stepsales/followups/send`
- `schedule_second_call` -> `POST /api/v1/stepsales/appointments/second-call`
- `send_payment_link` -> `POST /api/v1/stepsales/payments/link`
- `check_payment_status` -> `GET /api/v1/stepsales/payments/status/{payment_reference}`
- `mark_payment_received` -> `POST /api/v1/stepsales/payments/mark-received`
- `send_post_payment_request` -> `POST /api/v1/stepsales/post-sale/request-data`
- `search_jobs` -> optional enrichment endpoint
