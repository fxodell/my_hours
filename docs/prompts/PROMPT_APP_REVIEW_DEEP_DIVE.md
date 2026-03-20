# Prompt: Full app review — deep dive and doc updates

**Instructions for implementer:** Perform a deep-dive review of the entire MyHours application. Read the required docs and guardrails first, then systematically check code and links for issues. Finally, update the project docs so they stay accurate and useful.

## Required reading (before starting)

Read these in order:

1. **`docs/CONTEXT.md`** — Project overview, architecture, workflows, known gaps.
2. **`docs/TASKS.md`** — Current sprint, backlog, and completed items.
3. **`docs/DECISIONS.md`** — ADRs; ensure your review and any changes are consistent with them.
4. **`CLAUDE.md`** — Development commands, architecture, API summary, deployment, known issues.
5. **`.cursor/rules/guardrails.md`** — Rules for minimal changes, ADRs, CONTEXT updates, no throwaway files, etc. Apply these when editing.

## Review scope

### 1. Backend

- **API routes** (`backend/app/api/`): Auth, timesheets, reports, site_requests, pay_periods, employees, clients, locations, service_types. Check for missing auth/role checks, inconsistent error handling, and correct use of `CurrentUser` / `CurrentManager` / `CurrentAdmin`.
- **Models & schemas** (`backend/app/models/`, `backend/app/schemas/`): Alignment between DB models and Pydantic schemas; nullable vs required; relationships and `selectinload` usage in routes.
- **Core** (`backend/app/core/`): Config, database (async/sync engines), security (JWT, password hashing). No secrets in code; env-based config.
- **Reports** (`backend/app/api/reports.py`): Payroll, billing (with location/site code), hours-by-employee, hours-by-job-code, Engage export. Correct filters, ordering, and export formats (JSON, CSV, Excel).
- **Tests** (`backend/tests/`): Conftest fixtures, coverage of critical paths (auth, timesheet lifecycle, entry validation). Note any gaps or flakiness (e.g. session-scoped engine + committed data).

### 2. Frontend

- **Routes & guards** (`frontend/src/App.tsx`): All routes exist and use `ProtectedRoute`, `ManagerRoute`, or `AdminRoute` as appropriate. No broken or orphan routes.
- **Pages** (`frontend/src/pages/`): Dashboard, Timesheets, TimesheetDetail, TimeEntry, TimeEntryEdit, PTOEntry, PTOEntryEdit, Employees, SiteRequests, SiteRequestForm, Reports, etc. Check that links and navigation targets are correct (no 404s, correct query params like `?timesheet=<id>`).
- **Links**: Every internal `Link`/`to=` and `href` (menus, buttons, cards) points to a valid route. External links (if any) are intentional and safe.
- **API usage** (`frontend/src/services/api.ts`): Endpoints match backend; `fetchApi` and auth (token, 401 redirect) are used consistently. No hardcoded localhost in production paths.
- **Forms & state**: TanStack Query keys and invalidation; react-hook-form where used; timesheet editability and `timesheetStatus.ts` helpers applied consistently on entry pages.
- **Config** (`frontend/vite.config.ts`): Proxy target for `/api` (documented mismatch with `make dev` port 8000 vs 8002).

### 3. Cross-cutting

- **Health**: Backend exposes `/api/health`; Docker healthcheck and any test or script using `/health` should be aligned (see Known Issues).
- **Deployment**: `docs/DEPLOY_PRODUCTION.md` and CLAUDE.md deployment section. Restart script `scripts/production-restart-backend.sh` and sudo note for Docker. No contradictions.
- **Pay periods**: Not auto-created; seed and admin `POST /pay-periods/generate`. Pay period boundaries (e.g. Sun–Sat) documented where relevant.
- **Consistency**: CONTEXT.md, CLAUDE.md, and DECISIONS.md agree on architecture, workflows, and known issues. ADRs match current behavior (e.g. timesheet list sort: pay period then employee name; billing report columns).

### 4. Links and references

- **In-app links**: Nav, sidebar, “Add Time”, “Add PTO”, “Site Requests”, “Reports”, employee/timesheet detail links. Verify each target exists and access is allowed for the role.
- **Docs**: CONTEXT.md / CLAUDE.md references to file paths, endpoints, or ports are correct. TASKS.md items are still relevant; move or remove obsolete items.
- **DECISIONS.md**: Each ADR’s “Decision” and “Consequences” reflect the current code (e.g. if an ADR says “tiebreaker X” but code now uses Y, update the ADR).

## Deliverables

1. **Findings**  
   A concise list of issues found: bugs, security/access gaps, broken or misleading links, doc inaccuracies, technical debt, or inconsistencies. Group by area (backend, frontend, docs, config). Severity: critical / major / minor / nit.

2. **Doc updates**  
   Edit the following so they stay accurate and aligned with guardrails:

   - **`docs/CONTEXT.md`**  
     - Fix any wrong or outdated descriptions (architecture, workflows, key dirs, known gaps).  
     - Add or adjust bullets if the review reveals important behavior or gaps not yet documented.  
     - Keep “Known Gaps / Follow-ups” in sync with TASKS and CLAUDE known issues.

   - **`docs/TASKS.md`**  
     - Ensure Current Sprint and Backlog reflect real priorities; add any new issues from the review as tasks if they’re actionable.  
     - Mark completed items that are done; move or remove duplicates.  
     - Do not remove historical Completed items unless they’re wrong or obsolete.

   - **`docs/DECISIONS.md`**  
     - Update any ADR whose “Decision” or “Consequences” no longer match the code (e.g. timesheet list sort, billing report columns).  
     - Add a short ADR only if the review uncovers a new significant architectural or product decision that was made but not recorded.

3. **Optional code fixes**  
   If you fix critical or major issues (e.g. wrong auth, broken link, or incorrect health path), keep changes minimal and scoped. Add tests or manual test steps; update CONTEXT/TASKS/DECISIONS as needed. Follow `.cursor/rules/guardrails.md` (small diffs, ADR for architecture changes, no throwaway files).

## Out of scope

- Large refactors or new features beyond fixing clear bugs or doc drift.
- Changing third-party or generated files (e.g. lockfiles, build artifacts) unless necessary for the review (e.g. fixing a documented port mismatch).
- Production-only checks that require live credentials or SSH (e.g. running the app on the server); the review is code and docs based, with optional local run to verify links.

## Acceptance

- Required reading is done first; guardrails are followed when editing.
- Backend and frontend have been reviewed for auth, routes, links, and consistency with docs.
- CONTEXT.md, TASKS.md, and DECISIONS.md are updated so they accurately describe the app and known issues.
- Findings are listed clearly; any critical/major fixes are minimal and documented.
