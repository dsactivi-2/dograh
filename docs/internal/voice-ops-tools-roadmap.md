# Voice-Ops Tools Roadmap (dsactivi-2/dograh)

| Phase | Status | Deliverable |
|-------|--------|-------------|
| Config-Inventar | **done** | `docs/internal/config-defaults-inventory.md` |
| Data-Inventar Runs | **done** | `docs/internal/data-inventory-workflow-runs.md` |
| **P0** Outcomes + QA Schema | **MVP** | `/api/v1/outcomes/*`, Normalizer schema v1, UI `/analytics` |
| Disposition Taxonomy | **MVP** | `/api/v1/disposition-taxonomy/*`, Success-Set R/W on workflow |
| **P1** Script-Bibliothek | **MVP** | `/api/v1/scripts/*`, FTS prompt search, definition diff, UI `/scripts` |
| **P2** Text-Chat Eval Harness | **MVP core** | `/api/v1/evals/text/run`, UI `/evals` |
| **P3** Campaign Tower + Cost | **MVP** | `/api/v1/campaign-ops/*`, `/api/v1/cost-attribution/*`, UI `/campaigns/ops` + `/costs` |
| **P4** QA Center + Compliance | **MVP** | `/api/v1/qa-center/*`, UI `/qa-center`, override + audit |
| **P5** Schulung MVP | **MVP** | `/api/v1/training/*`, UI `/training`, shadow + text drills |
| **P6** Voice-Eval + Training-Voice | **MVP** | score-run + guarded SMALLWEBRTC + training voice; no dual-role |
| **P6 polish** Limits / deploy | **done** | env guards, pipeline duration cap, `/voice/guards`, deploy checklist |

## P0 Endpoints
- `GET /api/v1/outcomes/health`
- `GET /api/v1/outcomes/summary`
- `GET /api/v1/outcomes/runs`
- `GET /api/v1/outcomes/runs/{id}/qa`

## Disposition Taxonomy
- `GET /api/v1/disposition-taxonomy/summary` — org-wide code rollup
- `GET /api/v1/disposition-taxonomy/workflows/{id}`
- `PUT /api/v1/disposition-taxonomy/workflows/{id}` — body: disposition_codes, success_codes, code_meta

Stored on `workflows.call_disposition_codes` (backward-compatible extension).

## P1 Script Library
- `GET/POST /api/v1/scripts`
- `GET/PATCH/DELETE /api/v1/scripts/{id}`
- `GET /api/v1/scripts/search/prompts?q=` — Postgres FTS (`to_tsvector` / `plainto_tsquery`) + node extract
- `GET /api/v1/scripts/diff?definition_a=&definition_b=`
- Table `script_library_entries` (tags, owner, approval_status draft|pending|approved|rejected)
- Approval: owner or superuser
- UI: `/scripts` (cards, filters, FTS, diff, freigabe queue)

## P2 Text Eval
- `POST /api/v1/evals/text/run` — scenario JSON → TEXTCHAT session → assertions
- Assertion types: response_contains, response_not_contains, disposition_equals, gathered_key_exists, gathered_key_equals
- UI: `/evals`

## P3 Campaign Control Tower + Cost Attribution
- `GET /api/v1/campaign-ops/health`
- `GET /api/v1/campaign-ops/summary` — funnel + per-campaign retry/CB/disposition
- `GET /api/v1/campaign-ops/campaigns/{id}`
- `GET /api/v1/cost-attribution/health`
- `GET /api/v1/cost-attribution/summary?group_by=workflow|campaign|definition`
- UI: `/campaigns/ops`, `/costs`
- Docs: `docs/internal/campaign-control-tower.md`, `docs/internal/cost-attribution.md`
- Reuse: `queued_runs` + `workflow_runs` + `cost_info`/`usage_info` + existing CB Redis; no billing engine

## P4 QA Center + Compliance
- `GET /api/v1/qa-center/health|summary|queue`
- `GET /api/v1/qa-center/runs/{id}`
- `PUT /api/v1/qa-center/runs/{id}/override` — audit trail on annotations
- `POST /api/v1/qa-center/runs/{id}/rerun` — ARQ `run_integrations_post_workflow_run`
- Normalizer: dict-form tags + sentiment (`overall_sentiment`)
- Compliance flags: identity/disclosure/DNC/… from raw fields, tags, override
- UI: `/qa-center`
- Docs: `docs/internal/qa-center.md`
- Reuse: schema-v1 QA + annotations merge + ARQ; no new tables

## P5 Training / Schulung
- Tables: `training_modules`, `training_attempts` (migration `e4f5a6b7c8d9`)
- `GET/POST /api/v1/training/modules`
- `GET /api/v1/training/progress` — per-user completion
- `POST /api/v1/training/modules/{id}/shadow/complete` — quiz score
- `POST /api/v1/training/modules/{id}/text/run` — P2 text harness + success-set score
- UI: `/training`
- Docs: `docs/internal/training.md`
- Reuse: text-eval harness, disposition success codes, org auth

## P6 Voice Eval + Training Voice
- Phase 0: live pipeline + RTF transcripts + QA/disposition reuse; looptalk dual-role **removed**; no headless audio inject
- `POST /api/v1/evals/voice/score-run` — score completed run (transcript + assertions + success_codes + QA)
- `POST /api/v1/evals/voice/sessions` — create SHORT SMALLWEBRTC (`VEVAL-*`), rate-limited
- `POST /api/v1/evals/voice/sessions/{id}/finalize`
- Training: `mode=voice`, `POST .../voice/start|complete` (`VTRAIN-*`)
- Cost guards: default **5**/org/hour, batch=1, duration hint **60s** / hard **120s**, pipeline hard-cap, quota 402, `VOICE_EVAL_*` env
- `GET /api/v1/evals/voice/guards` · deploy: `docs/internal/voice-ops-deploy-checklist.md`
- UI: `/evals` Voice-Tab, `/training` voice modules
- Docs: `docs/internal/voice-eval.md`, `training-learning-design.md`
- Tests: `api/tests/test_voice_eval.py`
- **Not built:** dual-role, headless user-audio inject, unbounded batch voice

## UI typed clients (until OpenAPI regen)
- `ui/src/lib/api/outcomes.ts`
- `ui/src/lib/api/disposition.ts`
- `ui/src/lib/api/scripts.ts`
- `ui/src/lib/api/evals.ts`
- `ui/src/lib/api/campaignOps.ts`
- `ui/src/lib/api/costAttribution.ts`
- `ui/src/lib/api/qaCenter.ts`
- `ui/src/lib/api/training.ts`
- `ui/src/lib/api/evals.ts` (text + voice)

Regenerate hey-api client when API is running: `cd ui && npm run generate-client`.

## Reuse
Postgres JSON + FTS · ARQ post-call QA · Reports disposition · Org auth · Superuser · Text-chat runner · Campaign queued_runs · cost_info/usage_info · annotations override audit · training attempts · voice RTF transcripts · no Meilisearch/Celery · no looptalk
