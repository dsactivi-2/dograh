# Disposition Taxonomy (internal)

## Storage

Column: `workflows.call_disposition_codes` (JSON)

Legacy shape:

```json
{ "disposition_codes": ["XFER", "DNC"] }
```

Extended shape (v1):

```json
{
  "disposition_codes": ["XFER", "DNC", "NO_ANSWER"],
  "success_codes": ["XFER"],
  "code_meta": {
    "XFER": { "label": "Transfer", "category": "success", "description": "" }
  }
}
```

`add_call_disposition_code` preserves `success_codes` / `code_meta` when appending.

## API

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/v1/disposition-taxonomy/summary` | Org rollup |
| GET | `/api/v1/disposition-taxonomy/workflows/{id}` | Read |
| PUT | `/api/v1/disposition-taxonomy/workflows/{id}` | Replace taxonomy |

Auth: org-scoped via `get_user` + `selected_organization_id`.

## UI

`/analytics` — when a single workflow is selected, Success-Set chips can be toggled and saved.
