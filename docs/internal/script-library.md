# Script Library P1

## Table

`script_library_entries` — org-scoped entries linking workflows/definitions with:

- tags (JSON array)
- owner_user_id
- approval_status: `draft` | `pending` | `approved` | `rejected`
- approved_by_user_id / approved_at

Migration: `d1e2f3a4b5c6_add_script_library_entries.py`

## API

| Method | Path | Notes |
|--------|------|-------|
| GET/POST | `/api/v1/scripts` | List / create |
| GET/PATCH/DELETE | `/api/v1/scripts/{id}` | Owner or superuser for approve/delete |
| GET | `/api/v1/scripts/search/prompts?q=` | Postgres FTS on definition JSON + node extract |
| GET | `/api/v1/scripts/diff?definition_a=&definition_b=` | Prompt field diff |

## UI

`/scripts` — cards, status/tag filters, create form, FTS panel, definition diff, freigabe queue.
