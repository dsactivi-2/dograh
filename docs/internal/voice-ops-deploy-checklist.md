# Voice-Ops Deploy / Merge Checklist (P0–P6)

| Feld | Wert |
|------|------|
| **Datum (UTC)** | 2026-07-29 |
| **Branch** | `feature/stepsales-sales-api-mvp` |
| **Repo** | https://github.com/dsactivi-2/dograh |

## Pre-merge

- [ ] Branch rebased / fast-forward with target (`main` or release branch)
- [ ] Migrations applied on target DB:
  - Script library (P1) if not already
  - `e4f5a6b7c8d9_add_training_modules` (P5) — **required** for Training UI
  - P6 needs **no** new migration (`mode` is string; voice annotations only)
- [ ] `cd api && pytest --noconftest tests/test_voice_eval.py tests/test_training_score.py tests/test_text_eval_harness.py -q`
- [ ] Optional full suite when `DATABASE_URL` available
- [ ] UI typecheck / lint if CI expects it (`cd ui && npm run lint` / `tsc`)

## Env (production)

| Variable | Default | Notes |
|---|---|---|
| `VOICE_EVAL_ENABLED` | `true` | Set `false` to kill live voice sessions (score-run still works) |
| `VOICE_EVAL_MAX_SESSIONS_PER_ORG_HOUR` | `5` | VEVAL-* + VTRAIN-* count |
| `VOICE_EVAL_MAX_DURATION_HINT_SECONDS` | `60` | Default session budget |
| `VOICE_EVAL_HARD_MAX_DURATION_SECONDS` | `120` | Clamp + pipeline hard cap ceiling |

Restart API workers after changing these (process env, not hot-reload).

## Post-deploy smoke (dashboard)

1. Login → org selected  
2. `/analytics` loads  
3. `/scripts` list  
4. `/evals` Text: small scenario (optional, costs LLM)  
5. `/evals` Voice → **Cost-Guards** card shows numbers; **Score Run** on known completed voice run  
6. Optional: create 1 voice session, open workflow player / signaling, hang up ≤60s, Finalize  
7. `/training` shadow quiz  
8. `/qa-center` queue  
9. `/campaigns/ops` + `/costs`  
10. Confirm 6th voice session/hour → 429 (if testing limits)

## OpenAPI / typed client

Manual clients live under `ui/src/lib/api/*.ts` (outcomes, disposition, scripts, evals, campaignOps, costAttribution, qaCenter, training).

When API is running in the deploy env:

```bash
cd ui && npm run generate-client
```

Until regen: **keep manual clients** — they are the source of truth for new P0–P6 routes.

## Rollback

| Failure | Action |
|---|---|
| Voice sessions too expensive | `VOICE_EVAL_ENABLED=false` + restart API |
| Training UI 500 | check migration `e4f5a6b7c8d9` applied |
| Rate limit too tight | raise `VOICE_EVAL_MAX_SESSIONS_PER_ORG_HOUR` |
| Pipeline duration too short | raise hard max env (≤300) |

## Not in this release

- Dual-role / looptalk  
- Headless user-audio inject  
- Unbounded batch voice  
