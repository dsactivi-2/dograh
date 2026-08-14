# Data Inventory — Workflow Runs (Outcomes / QA)

| Feld | Wert |
|------|------|
| **Datum (UTC)** | 2026-07-28 |
| **Commit** | `bd9d220` / working tree |
| **Repo** | https://github.com/dsactivi-2/dograh |
| **Zweck** | Grundlage Outcomes-Dashboard + stabiles QA-Schema (P0) |

## 1. Primärquelle: `WorkflowRunModel`

**Datei:** `api/db/models.py` → `WorkflowRunModel`

| Spalte | Typ (semantisch) | Outcomes-Relevanz |
|--------|------------------|-------------------|
| `id` | int PK | Run-ID |
| `name` | string | Anzeige |
| `workflow_id` | FK Workflow | Agent-Filter |
| `definition_id` | FK Definition | Version |
| `mode` | enum/string | twilio/webrtc/textchat/… |
| `call_type` | `outbound` default | In/Outbound |
| `state` | `initialized` default | Lifecycle |
| `is_completed` | bool default false | Fertig? |
| `recording_url` / `transcript_url` | string? | Artefakte |
| `extra` | JSON `{}` | Zusatz |
| `storage_backend` | enum | S3/MinIO |
| `usage_info` | JSON | **Dauer:** `call_duration_seconds` |
| `cost_info` | JSON | Kosten |
| `initial_context` | JSON | **Phone:** `phone_number`, MPS correlation |
| `gathered_context` | JSON | **Disposition, Tags, Extracted Vars** |
| `logs` | JSON | `realtime_feedback_events` (Transcript-Events) |
| `annotations` | JSON | **QA-Ergebnisse** nach Integration-Task |
| `created_at` | timestamptz | Zeitraum-Filter |
| `campaign_id` | FK? | Campaign Tower später |
| `queued_run_id` | FK? | Retry-Kette |
| `public_access_token` | string? | Public Artifact URLs |

Org-Scope läuft über `WorkflowModel.organization_id` (Join), nicht direkt auf dem Run.

## 2. Outcome-Felder in `gathered_context` (bereits live)

| Key | Verwendung |
|-----|------------|
| `mapped_call_disposition` | Primäre Disposition (Daily Report, CSV) |
| `call_tags` | Liste Tags |
| `extracted_variables` | dict freier Extraktionen |
| weitere Keys | workflow-spezifisch |

**Reuse:** `api/services/reports/daily_report.py`, `run_report.py`, `api/db/reports_client.py` lesen genau diese Keys — **kein Meilisearch**.

## 3. QA in `annotations`

Geschrieben von `api/tasks/run_integrations.py` nach QA-Node-Lauf:

```
annotations = {
  "<qa_node_key>": {
    "node_results": {
      "<node_id>|whole_call": {
        "node_name": "...",
        "tags": [...],
        "summary": "...",
        "score": number|null,
        "error": optional
      }
    },
    "model": "..."
  },
  "tags": ["aggregated", ...],   # optional aggregiert
  ... integration results ...
}
```

**Instabil:** Freies LLM-JSON pro Node → P0 normalisiert zu stabilem Schema.

## 4. Disposition Codes

- Pro Workflow: `WorkflowModel.call_disposition_codes` JSON, typisch `{"disposition_codes": ["XFER", ...]}`
- Daily Report zählt `mapped_call_disposition`, Top-5 + Other
- Spezieller Code `XFER` → Transfer-Metrik

## 5. Bestehende APIs (Reuse)

| Endpoint | Was |
|----------|-----|
| `GET /api/v1/organizations/reports/daily` | Metrics + Disposition + Duration buckets |
| `GET /api/v1/organizations/reports/daily/runs` | Run-Details mit Disposition |
| `GET /api/v1/organizations/reports/workflows` | Workflow-Optionen |
| Usage / CSV exports | `build_run_report_csv` |

## 6. UI-Reuse

- `/reports` — Daily Disposition Charts (`DispositionChart`, `MetricsCards`, `DurationChart`)
- Sidebar MANAGE → Reports
- **Neu P0:** `/analytics` Outcomes-Dashboard (erweitert Reports, gleiche Datenquelle + QA-Normalizer)

## 7. Lücken für P0–P6

| Lücke | Impact | P0-Mitigation |
|-------|--------|---------------|
| Kein stabiles QA JSON Schema | Dashboard bricht bei Schema-Drift | Normalizer + Defaults |
| Keine Taxonomy-CRUD API | Codes nur pro Workflow | Read-only Aggregation zuerst |
| Kein Cross-Day Outcomes API | Nur daily | Date-range Endpoint |
| Script-Lib fehlt | P1 | Skeleton separat |
| Cost pro Provider unstrukturiert | P3 | `cost_info` inventarisieren später |

## 8. Prefer Reuse Checklist

- [x] Postgres Full-Text / JSON — kein Meilisearch
- [x] ARQ Tasks für post-call QA — kein Celery
- [x] MinIO/S3 Recordings — reuse
- [x] Superuser für Cross-Org Support — reuse
- [x] Daily reports + disposition — Outcomes v1 Basis
