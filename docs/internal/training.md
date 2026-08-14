# Training / Schulung MVP (P5)

| Feld | Wert |
|------|------|
| **Datum (UTC)** | 2026-07-29 |
| **Repo** | https://github.com/dsactivi-2/dograh |
| **Branch** | `feature/stepsales-sales-api-mvp` |
| **UI** | `/training` |
| **API** | `/api/v1/training/*` |

## Zweck

Schulungs-App für **Menschen** (Agenten/Reviewer):

1. **Shadow** — Script lesen + Quiz (ohne Live-Agent)
2. **Text-Drill** — scripted TEXTCHAT über den P2 Eval-Harness, Score vs. Assertions + Success-Set
3. **Voice** (P6) — kurze SMALLWEBRTC-Session + Score (Transcript/Disposition/QA)

Fortschritt pro User, org-scoped. Lernpfad: siehe `training-learning-design.md`.

## Tabellen

Migration `e4f5a6b7c8d9_add_training_modules.py`:

| Table | Inhalt |
|-------|--------|
| `training_modules` | Titel, mode, workflow_id?, success_codes, content JSON, pass_score, difficulty |
| `training_attempts` | user_id, module_id, score, passed, result JSON, workflow_run_id? |

## Endpoints

| Method | Path | Notes |
|--------|------|-------|
| GET | `/health` | |
| GET/POST | `/modules` | List (published) / Create |
| GET/PATCH/DELETE | `/modules/{id}` | Answers only for creator/superuser |
| GET | `/progress` | My completion % + per-module best |
| GET | `/attempts` | My attempts |
| POST | `/modules/{id}/shadow/complete` | Quiz answers → score |
| POST | `/modules/{id}/text/run` | Text drill via eval harness |
| POST | `/modules/{id}/voice/start` | SHORT SMALLWEBRTC run (`VTRAIN-*`) |
| POST | `/modules/{id}/voice/complete` | Score run → training_attempt |

## Content shapes

### Shadow

```json
{
  "script_excerpt": "…",
  "learning_points": ["…"],
  "quiz": [
    {
      "id": "q1",
      "prompt": "…",
      "options": [{"id": "a", "label": "…"}],
      "correct_option_ids": ["a"],
      "explanation": "…"
    }
  ]
}
```

Learner GET strips `correct_option_ids`.

### Text

```json
{
  "scenario_name": "training-greeting",
  "initial_context": {},
  "turns": [
    {
      "user": "Hallo?",
      "assertions": [
        { "type": "response_contains", "value": "hallo", "case_insensitive": true }
      ]
    }
  ],
  "final_assertions": []
}
```

Assertion types = P2 eval harness.

### Voice

```json
{
  "briefing": "…",
  "initial_context": {},
  "assertions": [
    { "type": "response_contains", "value": "hallo", "case_insensitive": true }
  ],
  "max_duration_hint_seconds": 90
}
```

Human-in-the-loop WebRTC. Cost guards: max 10 sessions/org/hour. No dual-role.

## Scoring

| Mode | Formel |
|------|--------|
| Shadow | % richtige Quiz-Fragen; passed if ≥ `pass_score` (default 70) |
| Text | 80% assertion pass-rate + 20% disposition ∈ `success_codes` |
| Voice | Voice-scorer: assertions + disposition + optional QA (siehe `voice-eval.md`) |

## Reuse

- P2 `run_text_eval_scenario` / text-chat session stack
- Script library link optional (`script_entry_id`)
- Disposition success set (same vocabulary as taxonomy)
- Org auth (`selected_organization_id`)

## UI

Sidebar MANAGE → **Training** → `/training`

Typed client: `ui/src/lib/api/training.ts`

## Tests

`api/tests/test_training_score.py` — pure scoring (no DB)
