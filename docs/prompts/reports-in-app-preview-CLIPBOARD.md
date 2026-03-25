# Reports in-app preview — paste into Claude Code

**Full spec (params, shapes, checklists):** `docs/prompts/reports-in-app-preview-claude-code.md`

Copy everything below the line into Claude Code CLI.

---

Implement in-app report **preview** on the MyHours Reports page using existing **JSON** report APIs; keep **CSV/Excel download** working with the same filters.

**Read first:** `docs/CONTEXT.md`, `CLAUDE.md`, `docs/prompts/reports-in-app-preview-claude-code.md`, `docs/prompts/PROMPT_REPORTS_EMPLOYEE_DETAIL_AND_SELF_EXPORT.md` for row semantics.

**Do not regress:** company scoping (`current_user.company_id`) in `backend/app/api/reports.py`; auth — `my-time-detail` is any authenticated user, other reports in use are manager/admin; Engage export stays **download-only** (no CSV-in-browser).

**Frontend:**
1. `frontend/src/services/api.ts` — Add typed `fetchApi` helpers with explicit `format=json`: my-time-detail, employee-detail (same query params as blob helpers), payroll by `pay_period_id`, billing with same `start_date`/`end_date` as current download (from selected pay period), biweekly (`period_group`, `anchor_start_date`). Map camelCase args to snake_case query strings. Optionally add hours-by-employee and hours-by-job-code JSON.
2. Add TS types for JSON responses (`types/reports.ts` or `types/index.ts`), including biweekly `data_quality_warnings` if present.
3. `frontend/src/pages/Reports.tsx` — Each section: a **Preview** action (TanStack Query — avoid refetch on every keystroke; use Preview button or `enabled: false` + fetch on demand) showing summary + scrollable table or mobile-friendly cards; keep existing download buttons. Show `row_count` for detail reports when API returns it. For biweekly, show warning banner if `data_quality_warnings` is non-empty. For Engage, short message that preview is N/A. Loading/error/empty states. Accessibility: sensible table labels.

**Backend:** None required unless you hit payload limits; JSON endpoints already exist in `backend/app/api/reports.py`.

**Limits to respect in UI messaging (API enforces):** date span max 366 days for detail reports; max 50 employees per employee-detail request.

**Verify:** `cd frontend && npm run lint && npm run build`. Spot-check preview totals match one CSV export for the same filters. Update `docs/CONTEXT.md` one short paragraph on preview + export.

**Out of scope:** charts, Engage CSV parsing, changing report grouping logic.
