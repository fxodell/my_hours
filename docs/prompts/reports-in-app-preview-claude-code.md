# Prompt: In-app report preview (JSON) + keep CSV/Excel download

**For:** Claude Code CLI / implementers  
**Paste-friendly (no tables):** [`reports-in-app-preview-CLIPBOARD.md`](./reports-in-app-preview-CLIPBOARD.md)  
**Goal:** Employees and managers/admins can **view** report results in the browser on the Reports page **without downloading first**. **Export** (CSV/Excel) must continue to work unchanged for equivalent filters.

---

## Related docs (read first)

- `docs/CONTEXT.md`, `CLAUDE.md` — project rules and architecture.
- `docs/prompts/PROMPT_REPORTS_EMPLOYEE_DETAIL_AND_SELF_EXPORT.md` — semantics of **day-grouped** rows, filters, and column meanings for `employee-detail` / `my-time-detail` JSON `data` rows (grouping excludes `description`, aggregate hours, etc.).
- `docs/prompts/PROMPT_PAYROLL_BIWEEKLY_ROLLUP.md` — biweekly rollup is **separate** from line-level detail; preview should not collapse the two UX-wise.

---

## Current state (do not regress)

| Layer | Facts |
|--------|--------|
| **Backend** | `backend/app/api/reports.py` — most handlers support `format=json` \| `csv` \| `excel`. Default for several routes is already **`json`**. |
| **Frontend** | `frontend/src/pages/Reports.tsx` only triggers **downloads** via `frontend/src/services/api.ts` (`fetchApiBlob`). Pay-period payroll hard-codes `format=csv`. |
| **Auth** | `GET /reports/my-time-detail` → `CurrentUser`. Other report routes in use → `CurrentManager` (manager or admin). |
| **Tenancy** | Queries use `current_user.company_id` (and/or PayPeriod company scoping). **Do not** weaken or bypass company filters when adding preview. |
| **Routing** | Reports live at `/reports` under `ProtectedRoute` (`frontend/src/App.tsx`); **all authenticated users** can open the page; manager sections are gated by `user.is_manager \|\| user.is_admin`. |

---

## API reference (exact query params)

Use **`fetchApi`** + `format=json` for preview. Mirror the **same** query strings as blob export except `format`.

### Detail reports (shared limits)

Defined in `reports.py`:

- **`_MAX_DATE_SPAN_DAYS = 366`** — `(end_date - start_date).days` must not exceed this; API returns **400** with a clear message.
- **`_MAX_EMPLOYEES_PER_REQUEST = 50`** for `employee-detail` — API returns **400** if more UUIDs in `employee_ids`.

**`timesheet_status`:** Omit or use `all` for no filter; otherwise comma-separated: `draft`, `submitted`, `approved`, `rejected`. Invalid tokens → **400**.

**`pay_period_status`:** Omit or `all`; or `open`, `closed`. Frontend today omits the param when `all` — keep that behavior for parity with download.

### `GET /api/reports/my-time-detail` (employee)

| Param | Required | Notes |
|--------|-----------|--------|
| `start_date` | yes | `YYYY-MM-DD` |
| `end_date` | yes | `YYYY-MM-DD` |
| `timesheet_status` | no | See above |
| `pay_period_status` | no | `open` \| `closed` \| omit/`all` |
| `include_pto` | no | default `true` |
| `format` | no | use `json` for preview |

**Never** send `employee_id` / `employee_ids` — server always scopes to the JWT user.

**JSON shape (approx.):** `{ report: "employee_detail", start_date, end_date, row_count, summary, grand_total, data }` — align types with `_run_detail_report` return in `reports.py`.

### `GET /api/reports/employee-detail` (manager/admin)

| Param | Required | Notes |
|--------|-----------|--------|
| `start_date` | yes | |
| `end_date` | yes | |
| `employee_id` | xor | single UUID |
| `employee_ids` | xor | comma-separated UUIDs |
| `timesheet_status`, `pay_period_status`, `include_pto`, `format` | no | same as my-time |

### `GET /api/reports/payroll` (manager/admin)

| Param | Notes |
|--------|--------|
| `pay_period_id` | optional UUID — filter to that pay period |
| `start_date`, `end_date` | optional — filter pay periods overlapping range (see existing SQL) |
| `format` | `json` \| `csv` \| `excel` |

**JSON shape:** `{ report: "payroll", data: [...] }` — rows include `employee_email`, `engage_id`, hours breakdowns, `pay_period_*`, `approved_at`.

**UI note:** Pay-period picker in `Reports.tsx` should drive **`pay_period_id`** for preview **and** download so results match.

### `GET /api/reports/billing` (manager/admin)

| Param | Notes |
|--------|--------|
| `client_id` | optional UUID |
| `start_date`, `end_date` | optional |
| `format` | |

**JSON shape:** `{ report: "billing", summary: { [client]: { hours, bonus_hours } }, data: [...] }`.

**UI note:** Today billing download uses pay period’s `start_date` / `end_date`. Preview must use the **same** dates for parity.

### `GET /api/reports/payroll-biweekly` (manager/admin)

| Param | Notes |
|--------|--------|
| `period_group` | `A` or `B` |
| `anchor_start_date` | `YYYY-MM-DD` — must match an existing period start for that group |
| `format` | |

**JSON shape:** includes `data` (rows with `hours_by_date`, aggregates, `missing_weeks`, etc.), metadata fields, and optional **`data_quality_warnings`** array — show in UI as a **warning banner**.

### `GET /api/reports/hours-by-employee` (manager/admin) — optional new section

| Param | Notes |
|--------|--------|
| `start_date`, `end_date` | optional |
| `format` | |

**JSON shape:** `{ report: "hours_by_employee", data: [...] }` — approved timesheets only.

### `GET /api/reports/hours-by-job-code` (manager/admin) — optional new section

| Param | Notes |
|--------|--------|
| `client_id` | optional |
| `start_date`, `end_date` | optional |
| `format` | |

**JSON shape:** `{ report: "hours_by_job_code", data: [...] }`.

### `GET /api/reports/engage-export` (manager/admin)

- **CSV only** (Engage import shape). **No JSON.**
- **Preview:** Do **not** implement CSV-in-browser unless product asks. Show copy: e.g. “Preview not available — download prepares Engage import CSV.”

---

## Implementation plan

### 1) API client (`frontend/src/services/api.ts`)

- Add typed **`fetchApi`** wrappers that set **`format=json`** (explicit), reusing the same query construction as existing blob helpers:

  - `getMyTimeDetailReportJson(...)`
  - `getEmployeeDetailReportJson(...)`
  - `getPayrollReportJson(payPeriodId)` — include `pay_period_id`; optional future: date-range for payroll if UI adds it
  - `getBillingReportJson({ startDate, endDate, clientId? })`
  - `getBiweeklyPayrollReportJson({ periodGroup, anchorStartDate })`

- Optionally: `getHoursByEmployeeJson`, `getHoursByJobCodeJson`.

- Add **TypeScript types** in `frontend/src/types/index.ts` or `frontend/src/types/reports.ts`:

  - Narrow types per endpoint where practical; use a shared **`ReportDetailResponse`** for my-time + employee-detail if shapes match.
  - Document optional **`data_quality_warnings`** on biweekly JSON.

- **Error handling:** Non-OK responses use JSON `detail` from backend (`ApiError`) — surface in preview error state.

### 2) Reports UI (`frontend/src/pages/Reports.tsx`)

For each report block:

1. **Preview** — TanStack **`useQuery`** with `queryKey` including **all** filter values (dates, employee ids sorted, pay period id, biweekly anchor, status filters, `include_pto`). Use **`enabled: false`** + **`refetch`** / **`queryClient.fetchQuery`** on a **“Preview”** button, **or** `enabled: true` only when user clicks Preview — avoid refetching on every keystroke.
2. **Download** — keep existing blob + `triggerDownload` behavior.

**Layout**

- Show **summary first** (`summary`, `grand_total`, billing `summary`, biweekly metadata) where JSON provides it.
- **Detail table** below: sortable header row where cheap; **horizontal scroll** on small screens **or** **card-per-row** layout for mobile (project is mobile-first).
- **Row count:** display `row_count` when present (employee / my-time detail).
- **Large responses:** No backend pagination initially — if table is huge, rely on scroll + optional note (“Showing full result — use export for Excel”). If product requires caps, add **backend** `limit` in a follow-up (out of scope unless specified).

**Loading / empty / error**

- Skeleton or spinner, empty state when `data.length === 0`, error banner with `detail` message.

**Accessibility**

- Table: `<table>` with scoped headers or `aria-label` describing the report.
- Focus management: optional — move focus to preview region on successful load.

**Print (optional)**

- Minimal `@media print` to hide nav/chrome if users “Print preview” from browser.

**Concurrent actions**

- Reuse pattern similar to `activeDownloads` for **preview** requests if double-click is possible (`isPreviewLoading` per section).

### 3) Backend changes

- **Default:** none — JSON already implemented.
- **Only if needed:** pagination or `limit` for detail JSON with same auth and `company_id` rules; document in OpenAPI and `docs/CONTEXT.md`.

### 4) Security & privacy

- Preview uses **same endpoints and roles** as download — **no** new data exposed to wrong tier.
- Do not add client-side filtering to “hide” sensitive columns for employees — employee routes already exclude other users’ data.

### 5) Verification

- `cd frontend && npm run lint && npm run build`
- Manually: employee account — my-time preview + download; manager — each manager section preview + download; confirm figures match between preview and exported file for one fixed filter set.
- **Optional:** backend test that `format=json` returns 200 and expected top-level keys for `my-time-detail` and one manager report.

### 6) Documentation

- Update **`docs/CONTEXT.md`**: Reports page supports in-browser **preview** (JSON) plus **CSV/Excel** export; Engage remains download-only.

---

## Acceptance criteria

- [ ] Employee can **preview** and **download** my-time detail with identical filter semantics.
- [ ] Manager/admin can **preview** and **download** employee detail, biweekly rollup, payroll (by pay period), billing (same date range as today’s download).
- [ ] **`data_quality_warnings`** visible for biweekly when present.
- [ ] Engage: download only + clear UI text.
- [ ] No regression in company isolation; no new global queries.
- [ ] Optional: hours-by-employee / hours-by-job-code preview sections for managers.

---

## Out of scope (unless explicitly requested)

- New charting libraries, dashboards, scheduled emails.
- Parsing Engage CSV for in-browser display.
- Changing report business logic or grouping (see separate prompts for that).

---

## Implementation reminder

- Parameter names in HTTP query strings are **`snake_case`** (`start_date`, `employee_ids`, `anchor_start_date`, …); frontend helpers may take **`camelCase`** and map when building `URLSearchParams`.
- Backend default `format` is often `json`; still pass **`format=json`** explicitly in preview calls for clarity and stable OpenAPI expectations.
