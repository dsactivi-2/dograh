# Handover – Stepsales Sales API MVP – 2026-07-29

## Context

Previous session (2026-05-13) shipped the Stepsales workflow template pack (18 templates) and documented the next build phase: real sales tools + API endpoints.

This session implements that phase as a **testable first MVP** on `dsactivi-2/dograh` (branch `feature/stepsales-sales-api-mvp`).

## What was built

### Backend (Dograh API)

- Org-scoped SQLAlchemy models for leads, call outcomes, offers, followups, appointments, payments, events
- Alembic migration `a1b2c3d4e5f6`
- Service layer with scoring, package catalog, max 10% discount, status vocabulary
- REST routes under `/api/v1/stepsales/*`
- Auth via existing `get_user` (JWT / `X-API-Key`)
- Unit + route tests (`api/tests/test_stepsales_*.py`)

### Docs & templates

- `docs/stepsales/README.md` — operator guide
- Specs copied from dograhv1: tools guide + API spec + prior handover
- `stepsales/templates/` — 18-template pack (JSON) for import into `workflow_templates`

## How main can test

1. Merge / pull the branch into the deploy that runs Dograh API
2. `alembic upgrade head` (or specifically `a1b2c3d4e5f6`)
3. Create or reuse an org API key
4. Hit `/api/v1/stepsales/health` then the qualify → outcome → offer flow in `docs/stepsales/README.md`
5. Optionally import templates from `stepsales/templates/stepsales_templates.json` / SQL seed from dograhv1
6. Point Dograh HTTP tools (webhooks) at the new endpoints using the tool→endpoint mapping in `13_sales_api_spec.md`

## Explicit MVP gaps (not bugs)

- Email delivery is logged as `queued` only
- Payment links are mock URLs
- Job search is mock enrichment
- Template JSON is not yet re-bound to the new tool URLs automatically

## Suggested next steps

1. Seed HTTP tools in Dograh that call these endpoints
2. Wire SMTP / Stripe
3. Light operator UI for lead pipeline
4. Re-export templates with webhook nodes pointing at `/api/v1/stepsales/...`

## Security note

Do not commit real API keys. Rotate any keys that were previously shared in chat.
