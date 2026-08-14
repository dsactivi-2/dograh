# QA Center + Compliance (P4)

| Feld | Wert |
|------|------|
| **Datum (UTC)** | 2026-07-28 |
| **Repo** | https://github.com/dsactivi-2/dograh |
| **Branch** | `feature/stepsales-sales-api-mvp` |
| **UI** | `/qa-center` |
| **API prefix** | `/api/v1/qa-center` |

## Zweck

Org-scoped **Review-Zentrale** für post-call QA:

- Aggregation von Tags, Scores (1–10), Sentiment
- Review-Queue: Low-Score, Problem-Tags, Compliance-Fails, QA-Errors
- Manuelles Override mit Audit-Trail
- Optionaler QA Re-Run über bestehende ARQ-Task `run_integrations_post_workflow_run`

## Endpoints

| Method | Path | Beschreibung |
|--------|------|--------------|
| GET | `/health` | Modul-Health + Default-Tags/Threshold |
| GET | `/summary` | Aggregation Zeitraum / Workflow |
| GET | `/queue` | Review-Queue (paginiert, sortiert) |
| GET | `/runs/{id}` | Detail + Audit-History |
| PUT | `/runs/{id}/override` | Manuelles Override speichern |
| POST | `/runs/{id}/rerun` | ARQ Re-Run der Post-Call-Integrationen (QA) |

### Query-Parameter (summary/queue)

- `from_date`, `to_date` (YYYY-MM-DD), `timezone` (IANA)
- `workflow_id` optional
- `max_score` — Low-Score-Schwelle (Default **6**, Skala 1–10)
- `problem_tags` — kommagetrennt (Default: Dograh-Standard-Tags)
- `only_needs_review` (queue, default true)

## Datenquellen (Reuse)

| Quelle | Verwendung |
|--------|------------|
| `workflow_runs.annotations` | Auto-QA (`node_results`) + Override-Keys |
| Schema-v1 Normalizer | `api/services/outcomes/normalize.py` |
| `gathered_context.mapped_call_disposition` | Disposition-Anzeige |
| ARQ `run_integrations_post_workflow_run` | Re-Run |

**Keine** neue Tabelle, **kein** Meilisearch/Celery.

## Override-Speicher (Audit)

Unter `annotations`:

```json
{
  "qa_manual_override": {
    "schema_version": 1,
    "overall_score": 8,
    "sentiment": "neutral",
    "tags": ["REVIEWED_OK"],
    "summary": "…",
    "notes": "Reviewer notes",
    "compliance_flags": { "identity_verified": true, "disclosure_made": true },
    "reviewer_user_id": 42,
    "reviewer_email": "rev@example.com",
    "created_at": "ISO-8601",
    "previous": { "…prior override without nested previous…" }
  },
  "qa_override_audit": [
    { "at": "…", "reviewer_user_id": 42, "override": { } }
  ]
}
```

DB-Client merged annotations shallow (`{**existing, **patch}`) — Auto-QA-Keys bleiben erhalten.

## Compliance-MVP

Flags (pass/fail/unknown):

| Key | Label | Quellen |
|-----|-------|---------|
| `identity_verified` | Identity verified | raw field / tag / override |
| `disclosure_made` | Disclosure made | raw field / tag / override |
| `recording_notice` | Recording notice | raw field / tag / override |
| `dnc_respected` | DNC respected | raw field / tag / override |
| `options_presented` | Options presented | raw field / tag / override |
| `minors_policy` | Minors policy | raw field / override |
| `consent_obtained` | Consent obtained | raw field / tag / override |

Custom QA-Prompts, die booleans in den JSON-Output schreiben (siehe `docs/voice-agent/qa.mdx`), werden aus `node_results.*.raw` gelesen. Tags mit `IDENTITY` / `DISCLOSURE` / … markieren Fail.

## Default Problem-Tags

`DEAD_AIR`, `USER_FRUSTRATED`, `ASSISTANT_IN_LOOP`, `ASSISTANT_REPLY_IMPROPER`, `USER_NOT_UNDERSTANDING`, `HEARING_ISSUES`, `UNCLEAR_CONVERSATION`, `ASSISTANT_LACKS_EMPATHY`, `USER_DETECTS_AI`

## UI

Sidebar MANAGE → **QA Center** → `/qa-center`

Typed client: `ui/src/lib/api/qaCenter.ts`

## Auth

Org-Scope via `user.selected_organization_id` + `get_workflow_run(..., organization_id=)`.

## Tests

- `api/tests/test_qa_center_enrich.py` — override, compliance, queue rules, summary
- `api/tests/test_outcomes_normalize.py` — dict-tags, sentiment, skip override key
