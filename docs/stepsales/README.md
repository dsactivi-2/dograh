# Stepsales Sales API MVP

First real backend layer for the Stepsales multiposting telesales motion on Dograh.

This is **not a prototype**: the endpoints persist org-scoped data, validate business rules (max 10% discount, package catalog, scoring), and are ready for main-branch testing via API key auth.

## What shipped

| Tool | Endpoint | Status |
|------|----------|--------|
| `log_call_outcome` | `POST /api/v1/stepsales/calls/outcome` | MVP |
| `qualify_lead` | `POST /api/v1/stepsales/leads/qualify` | MVP |
| `create_offer` | `POST /api/v1/stepsales/offers/create` | MVP |
| `send_followup` | `POST /api/v1/stepsales/followups/send` | MVP (queued) |
| `schedule_second_call` | `POST /api/v1/stepsales/appointments/second-call` | MVP |
| `send_payment_link` | `POST /api/v1/stepsales/payments/link` | MVP (mock link) |
| `check_payment_status` | `GET /api/v1/stepsales/payments/status/{ref}` | MVP |
| `mark_payment_received` | `POST /api/v1/stepsales/payments/mark-received` | MVP |
| `send_post_payment_request` | `POST /api/v1/stepsales/post-sale/request-data` | MVP (queued) |
| `search_jobs` | `POST /api/v1/stepsales/jobs/search` | optional mock |

Extra for operators:

- `GET /api/v1/stepsales/health` (public)
- `GET /api/v1/stepsales/packages` (auth)
- `GET /api/v1/stepsales/leads` / `GET /api/v1/stepsales/leads/{lead_id}` (auth)

## Auth

Use a Dograh org API key:

```bash
curl -s -H "X-API-Key: $DOGRAH_API_KEY" \
  http://localhost:8000/api/v1/stepsales/packages
```

## Migration

```bash
cd api
alembic upgrade head
```

Revision: `a1b2c3d4e5f6_add_stepsales_sales_tables` (down_revision `00b0201ad918`).

If your deploy has multiple alembic heads, merge or run:

```bash
alembic upgrade a1b2c3d4e5f6
```

## Happy-path smoke (after migrate + API running)

```bash
export DOGRAH_API_KEY=...
export BASE=http://localhost:8000/api/v1/stepsales

# 1) Qualify
curl -s -X POST "$BASE/leads/qualify" \
  -H "X-API-Key: $DOGRAH_API_KEY" -H "Content-Type: application/json" \
  -d '{
    "company_name":"TechCorp GmbH",
    "contact_name":"Max Müller",
    "role":"HR Manager",
    "email":"max@techcorp.de",
    "phone":"+49301234567",
    "active_hiring":true,
    "roles_hiring_for":["Software Engineer","Sales Manager"],
    "urgency":"high",
    "timeline":"2 weeks",
    "budget_signal":"open",
    "interest_level":"high",
    "next_step":"send_offer"
  }'
# → lead_id, score, status=qualified

# 2) Log call outcome (use lead_id from step 1)
# 3) Create offer package MULTI_M with optional ≤10% discount
# 4) Send follow-up / payment link / mark received / post-sale request
```

See `13_sales_api_spec.md` for full request/response contracts and
`12_tools_setup_guide.md` for wiring into Dograh workflow HTTP tools.

## Package catalog

| ID | Name | List price |
|----|------|------------|
| `MULTI_S` | Multiposting Paket S | 790 |
| `MULTI_M` | Multiposting Paket M | 1490 |
| `MULTI_L` | Multiposting Paket L | 2490 |

Max discount: **10%**. Discount reason is required when discount > 0. Final price is always computed server-side.

## MVP boundaries (honest)

- Follow-up and post-sale emails are **persisted as `queued`** — SMTP/provider wiring is next.
- Payment links are **local mock URLs** (`https://payments.stepsales.local/pay/...`) — Stripe/provider is next.
- `search_jobs` returns **stable mock context**, never a hard dependency for close path.
- Workflow HTTP tools still need to be pointed at these endpoints in the UI (or seed script).

## Code map

```
api/routes/stepsales.py
api/schemas/stepsales.py
api/services/stepsales/
api/db/stepsales_client.py
api/db/models.py          # Stepsales* models
api/alembic/versions/a1b2c3d4e5f6_add_stepsales_sales_tables.py
api/tests/test_stepsales_*.py
stepsales/templates/      # 18 workflow templates (from dograhv1 pack)
docs/stepsales/
```

## Next after this MVP

1. Wire Dograh HTTP tools / webhooks to these endpoints in the Stepsales templates
2. Real mail provider for follow-ups
3. Real payment provider for payment links
4. Optional UI surface for lead/offer/payment overview
