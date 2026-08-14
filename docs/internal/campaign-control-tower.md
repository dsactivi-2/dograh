# Campaign Control Tower (P3)

| Feld | Wert |
|------|------|
| **Datum (UTC)** | 2026-07-28 |
| **Phase** | P3 MVP |
| **Repo** | https://github.com/dsactivi-2/dograh |
| **Branch** | `feature/stepsales-sales-api-mvp` |

## Zweck

Org-scoped Operations-Sicht über Campaigns: Funnel **queued → dialed → connected → disposition**, Retry- und Circuit-Breaker-Visibility. **Reuse** von `campaigns`, `queued_runs`, `workflow_runs` — keine neue Orchestrator-Engine.

## Endpoints

| Method | Path | Auth |
|--------|------|------|
| GET | `/api/v1/campaign-ops/health` | none |
| GET | `/api/v1/campaign-ops/summary` | user + org |
| GET | `/api/v1/campaign-ops/campaigns/{id}` | user + org |

### Query (`summary`)

- `from_date`, `to_date` — `YYYY-MM-DD`
- `timezone` — IANA (default `UTC`)
- `campaign_id` — optional
- `workflow_id` — optional

## Datenquellen

| Signal | Quelle |
|--------|--------|
| Queue funnel | `queued_runs.state` ∈ `queued` / `processing` / `processed` / `failed` |
| Connected | Heuristik: completed run + duration > 0 **oder** Disposition ≠ no-connect set |
| Disposition | `workflow_runs.gathered_context.mapped_call_disposition` |
| Retry config | `campaigns.retry_config` |
| Retry counts | `queued_runs.retry_count` / `retry_reason` |
| Circuit breaker config | `campaigns.orchestrator_metadata.circuit_breaker` |
| Circuit breaker live | Redis via `CircuitBreaker.is_circuit_open` (best-effort; `source=unavailable` wenn Redis down) |

## UI

- Route: **`/campaigns/ops`**
- Sidebar MANAGE → **Campaign Ops**
- Typed client: `ui/src/lib/api/campaignOps.ts`

## Nicht im Scope

- Meilisearch / Celery
- Neue Campaign-State-Machine
- Cross-org (nur Superuser-Flows existieren separat)
