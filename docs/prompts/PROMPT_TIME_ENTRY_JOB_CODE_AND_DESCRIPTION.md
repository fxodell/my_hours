# Time entry: required job code (when location has codes) + required description on create

Use this prompt in **Agent mode** or Claude Code.

---

Read `docs/CONTEXT.md` and `CLAUDE.md` and follow project conventions (minimal diffs, backend as source of truth, tests, update `docs/CONTEXT.md` if behavior changes).

## Goal

1. **Conditional job code (create)**  
   When creating a time entry, if the user selects a **location** that has **one or more** active job codes available, **job code** must be required.  
   If the location has **no** job codes (or no location selected), **job code** remains optional as today.

2. **Required description / notes (create)**  
   For **new** time entries only (`POST` create), the work **description** field (`description` in API / “Description of Work” in UI) must be **required**: non-empty after trim.

## Implementation guidance

**Backend** (`backend/app/api/timesheets.py` — `create_time_entry`, and schemas in `backend/app/schemas/time_entry.py`):

- Enforce **description** on create: e.g. validate `entry_data.description` is present and `strip()` non-empty; return `400` with a clear message if not.
- Enforce **job_code_id** when the chosen `location_id` has associated active job codes:
  - Query `JobCode` for `location_id` + company scope + `is_active=True` (match how locations/job codes are listed elsewhere).
  - If count > 0 and `job_code_id` is missing, return `400`.
  - If count == 0, do not require `job_code_id`.
  - Optionally verify `job_code_id` belongs to that location if provided (defense in depth).
- Prefer **explicit checks in the route** or a small helper so rules stay obvious; align with Pydantic models (either field validators with context, or post-schema validation in the handler — pick one clear pattern).

**Frontend** (`frontend/src/pages/TimeEntry.tsx`):

- Add UX validation before submit: **description** required (trim).
- When `jobCodes` for the selected location exists and `length > 0`, require **job code** (react-hook-form rules or submit guard consistent with backend).
- Show field-level or form-level errors matching backend messages where practical.

**Scope note:** Request is for **new** entries only; limit backend enforcement to **create**. If mirroring rules on **edit** (`TimeEntryUpdate` / `TimeEntryEdit.tsx`), call that out in the diff and in `CONTEXT.md` — default is **create-only** unless consistency is worth expanding scope.

**Tests** (`backend/tests/` — find existing time entry create tests):

- Create with location that has job codes but no `job_code_id` → `400`.
- Create with description blank/whitespace → `400`.
- Create with location with no job codes, no `job_code_id` → still `201` (if other fields valid).
- Create with valid description and required job code when codes exist → `201`.

**Docs**

- Update `docs/CONTEXT.md` briefly under time entry / validation behavior.
- If end-user wording changes (e.g. “Description of Work” now required), update `UserReadMe.md` in the logging-time section only if copy changes.

## Files likely involved

- `backend/app/api/timesheets.py` (`create_time_entry`)
- `backend/app/schemas/time_entry.py` (`TimeEntryCreate` — optional tightening vs validation in route)
- `backend/app/models/job_code.py` / job code queries
- `frontend/src/pages/TimeEntry.tsx`
- Tests under `backend/tests/`
