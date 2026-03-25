# Location request approval — dropdown refresh + naming

Use this prompt in **Agent mode** (or Claude Code) when fixing stale location lists after a manager approves a location request, and aligning UI copy with “Location” terminology.

---

Read `docs/CONTEXT.md` and `CLAUDE.md` for project conventions.

**Problem:** After a manager approves a site request at `/site-requests`, the new row should appear in the **Location** dropdown on Add Time (`frontend/src/pages/TimeEntry.tsx`) / edit time (`frontend/src/pages/TimeEntryEdit.tsx`) without requiring a manual full page refresh. CONTEXT says approval creates a `Location` in `backend/app/api/site_requests.py` — verify that path, then trace the frontend: locations are loaded with TanStack Query keys like `['locations', selectedClientId]`. Today `frontend/src/pages/SiteRequests.tsx` only invalidates `['siteRequests']` on approve; that likely leaves cached locations stale — fix by invalidating location (and job code) queries on approve success (and consider the same after reject if needed). Use the same invalidation patterns as `frontend/src/pages/Locations.tsx` where appropriate.

**Naming:** User-facing copy should say **Location request** (not “site request”) everywhere it refers to this workflow, to stay consistent with “Locations” in the app (pages, nav, buttons, modals, success toasts, empty states). Keep scope to user-visible strings unless product wants URL changes too.

**Tests:** Add or extend a small test if there’s an existing pattern (e.g. frontend integration isn’t required if not in repo; backend tests already exist in `backend/tests/test_site_requests.py`).

**Docs:** Update `docs/CONTEXT.md` only if behavior doc changes (e.g. cache/refresh expectation).

**Related:** `docs/DECISIONS.md` ADR-001 (site request workflow), `docs/prompts/PROMPT_SITE_REQUEST_DOCS.md`.
