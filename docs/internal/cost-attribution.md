# Cost Attribution Dashboard (P3)

| Feld | Wert |
|------|------|
| **Datum (UTC)** | 2026-07-28 |
| **Phase** | P3 MVP |
| **Repo** | https://github.com/dsactivi-2/dograh |
| **Branch** | `feature/stepsales-sales-api-mvp` |

## Zweck

Kosten pro **Workflow / Campaign / Definition** aus vorhandenen Run-Feldern aggregieren. **Kein neues Billing** — reuse `cost_info` + `usage_info` (+ bestehende `organization_usage`-Semantik für Duration/Tokens).

## Endpoints

| Method | Path | Auth |
|--------|------|------|
| GET | `/api/v1/cost-attribution/health` | none |
| GET | `/api/v1/cost-attribution/summary` | user + org |

### Query

- `from_date`, `to_date`, `timezone`
- `workflow_id`, `campaign_id` — optional filter
- `group_by` — `workflow` \| `campaign` \| `definition` (default `workflow`)

## Defensive Extraction

Aus `workflow_runs.cost_info` / `usage_info` (siehe `api/services/cost_attribution/extract.py`):

| Feld | Verwendung |
|------|------------|
| `cost_info.total_cost_usd` | primäre USD-Attribution |
| `cost_info.charge_usd` | Fallback USD / charge total |
| `cost_info.dograh_token_usage` | Token-Summe (oder abgeleitet aus `total_cost_usd * 100`) |
| `usage_info.call_duration_seconds` | Duration |

- Runs **ohne** monetary fields → `runs_missing_cost`, Notes im Response
- Keine erfundene USD-Preisbildung aus Duration in diesem Modul (Org-Pricing bleibt bei `organization_usage`)

## UI

- Route: **`/costs`**
- Sidebar MANAGE → **Costs**
- Typed client: `ui/src/lib/api/costAttribution.ts`
- Link zu `/usage` (Agent Runs) für Run-Detail

## Reuse

- Org-Scope via `WorkflowModel.organization_id` join (wie Outcomes / Usage)
- Max 10k rows pro Summary-Fenster (date range eng halten)
- Keine MPS-Ledger-Duplikation — Ledger bleibt `/billing`
