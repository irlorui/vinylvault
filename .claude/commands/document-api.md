# Document API Skill

Generate or update the API reference documentation for VinylVault.

## Usage
```
/document-api
```

## Behavior

1. **Read sources** — scan `src/backend/main.py` for all routes (method, path, status code, response model) and `src/backend/models.py` for request/response schemas.

2. **Read `src/backend/score.py`** for `WIN_SCORE` and any game constants that affect API behaviour.

3. **Write `docs/api.md`** — create or fully overwrite the file with the sections below. Never append; always regenerate from source so the doc stays in sync.

4. **Update the API table in `README.md`** — find the `**API endpoints:**` table and replace it to match the current routes. Keep the table concise (method, path, description only).

5. **Run `make pre-commit`** to verify nothing broke.

## Output format for `docs/api.md`

### Structure

```markdown
# API Reference

Base URL: `http://127.0.0.1:8000`

## Endpoints

### <METHOD> <path>

**Description:** ...
**Response:** `<status>` — `<ResponseModel>`

#### Response body
| Field | Type | Description |
|-------|------|-------------|

#### Errors
| Status | Meaning |
|--------|---------|

---
```

### Rules
- List endpoints in the order they appear in `main.py`.
- For `204 No Content` responses, omit the response body table.
- Document every non-2xx status code that the route or the underlying spotify.py function can raise (look for `HTTPException` calls).
- For models, derive field descriptions from field names and docstrings — do not invent behaviour.
- Include a **Game constants** section at the end listing `WIN_SCORE` and its effect on `POST /api/score/add`.
- Keep language concise and technical — this doc is for developers, not end users.