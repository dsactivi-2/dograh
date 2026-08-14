# Wire Stepsales tools as Dograh HTTP tools

Dograh agents call external tools via the Tools UI (`HTTP API` category).  
For each Stepsales tool, create one HTTP tool pointing at your Dograh API base.

## Prerequisites

- Stepsales migration applied
- Org API key available
- Base URL e.g. `https://your-dograh-host` (or internal `http://api:8000` in compose)

## Common config

| Field | Value |
|-------|--------|
| Method | `POST` (except payment status = `GET`) |
| Header `Content-Type` | `application/json` |
| Header `X-API-Key` | `{{org_api_key}}` or fixed org key secret |
| Timeout | 15–30s |

## Tool → URL mapping

| Tool name | Method | Path |
|-----------|--------|------|
| `log_call_outcome` | POST | `/api/v1/stepsales/calls/outcome` |
| `qualify_lead` | POST | `/api/v1/stepsales/leads/qualify` |
| `create_offer` | POST | `/api/v1/stepsales/offers/create` |
| `send_followup` | POST | `/api/v1/stepsales/followups/send` |
| `schedule_second_call` | POST | `/api/v1/stepsales/appointments/second-call` |
| `send_payment_link` | POST | `/api/v1/stepsales/payments/link` |
| `check_payment_status` | GET | `/api/v1/stepsales/payments/status/{payment_reference}` |
| `mark_payment_received` | POST | `/api/v1/stepsales/payments/mark-received` |
| `send_post_payment_request` | POST | `/api/v1/stepsales/post-sale/request-data` |
| `search_jobs` | POST | `/api/v1/stepsales/jobs/search` |

## Recommended first tools to enable in voice workflows

1. `qualify_lead`
2. `log_call_outcome`
3. `create_offer`
4. `send_followup`

Attach these tools to the Stepsales Main templates once created.

## Parameter notes

- Prefer passing `lead_id` returned by `qualify_lead` into all subsequent tools.
- `create_offer.package_id` must be one of `MULTI_S | MULTI_M | MULTI_L`.
- `discount_percent` max `10`; always send `discount_reason` when > 0.
- Never invent payment confirmation — use `mark_payment_received` only after real confirmation.
