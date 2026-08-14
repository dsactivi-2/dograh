# Voice Eval + Training Voice (P6)

| Feld | Wert |
|------|------|
| **Datum (UTC)** | 2026-07-29 |
| **Repo** | https://github.com/dsactivi-2/dograh |
| **Branch** | `feature/stepsales-sales-api-mvp` |
| **UI** | `/evals` (Voice-Tab), `/training` (mode=voice) |
| **API** | `/api/v1/evals/voice/*`, `/api/v1/training/modules/{id}/voice/*` |

## Phase 0 — Verifikation (Kurz)

| Capability | Status | P6 |
|---|---|---|
| SMALLWEBRTC + telephony pipeline | vorhanden | Session-Create |
| Transcript aus RTF events | vorhanden | Score |
| QA schema v1 + QA Center | vorhanden | Score optional |
| Disposition success codes | vorhanden | Score |
| Text-eval harness | vorhanden | Template |
| Training shadow/text | vorhanden | + voice mode |
| Looptalk dual-role | **entfernt** | BLOCKED |
| Headless user-audio inject | **fehlt** | DEFERRED |

## Was gebaut (MVP)

### A) Score bestehenden Run (kostenlos)

`POST /api/v1/evals/voice/score-run`

- Input: `workflow_run_id`, optional assertions, success_codes, include_qa
- Transcript: `logs.realtime_feedback_events` → `generate_transcript_text`
- Score: Assertions 70% + Disposition 20% + QA 10% (wenn QA da); sonst 80/20
- Stamp: `annotations.voice_eval`

### B) Bewachte WebRTC-Session

`POST /api/v1/evals/voice/sessions` → SMALLWEBRTC run (`VEVAL-*`)

`POST /api/v1/evals/voice/sessions/{run_id}/finalize`

- Client verbindet über existierendes Signaling:  
  `/api/v1/ws/signaling/{workflow_id}/{run_id}`
- **Kein** Audio-Inject, **kein** Dual-Role
- Guards: max 5 Sessions/Org/Stunde (env), batch=1, duration ≤120s hard + **pipeline cap**
- Quota: `authorize_workflow_run_start` (402)

### C) Training Voice

- Module `mode=voice` (kein Schema-Migration — `mode` ist String)
- `POST .../voice/start` → `VTRAIN-*` SMALLWEBRTC
- `POST .../voice/complete` → Score + `training_attempts`

## Cost Guards (production polish)

| Guard | Default | Env |
|-------|---------|-----|
| Max sessions / org / hour | **5** (`VEVAL-%` + `VTRAIN-%`) | `VOICE_EVAL_MAX_SESSIONS_PER_ORG_HOUR` |
| Max batch | 1 | fixed |
| Duration hint default | **60s** | `VOICE_EVAL_MAX_DURATION_HINT_SECONDS` |
| Hard clamp | **120s** | `VOICE_EVAL_HARD_MAX_DURATION_SECONDS` |
| Feature kill switch | on | `VOICE_EVAL_ENABLED` |
| Pipeline hard-cap | **an** | reads `initial_context.voice_eval|training_voice.max_duration_hint_seconds` in `run_pipeline` |

Status: `GET /api/v1/evals/voice/guards` · health embeds `voice.guards`.

Unbounded batch voice remains **verboten**.

## Scoring-Reuse

- Assertions: `text_harness.evaluate_assertion` auf Transcript
- QA: `outcomes.normalize_run_qa` (schema v1)
- Training: `score_voice_drill` wrappt voice score → attempt

## Bewusst nicht

| Item | Status |
|------|--------|
| Headless STT-Audio-Inject | DEFERRED |
| Dual-role / Looptalk | BLOCKED_EXTERNAL (tables dropped) |
| Batch voice suite runner | DEFERRED (cost) |
| Telephony auto-dial for eval | DEFERRED |

## Tests

`api/tests/test_voice_eval.py` — pure unit (no DB)

## UI checklist

- [ ] `/evals` → Tab Voice → Score Run mit vorhandener Run-ID
- [ ] `/evals` → Session anlegen → Run-ID + Signaling-Pfad
- [ ] Nach Call → Finalize → Transcript + Score
- [ ] `/training` → Modul Voice anlegen → Start → Complete
- [ ] Rate-Limit: 6. Session → 429 (default 5/h)
- [ ] `GET /evals/voice/guards` + Cost-Guards card on `/evals` Voice
- [ ] Pipeline hangs up at max_duration_hint (not full 300s)
- [ ] QA Center: Run mit `annotations.voice_eval` sichtbar
