# Prompt: Employee detail reports (draft-capable, multi-employee) + self-service export

**Instructions for implementer:** Extend reporting so **managers and admins** can run **date-range** exports for **one or many employees**, including **draft / unapproved** timesheets (to preview work in progress), with clear filters. **Employees** must be able to **download their own** hours for **draft**, **submitted**, **approved**, and **rejected** timesheets, and optionally rows where the **pay period is closed**. Align auth so employees never see other users’ data.

## Relationship to other reports (do not merge endpoints)

- **This prompt** — **Line-level**: typically **one row per `TimeEntry`** (and optional **one row per `PTOEntry`**), with status filters. Supports **draft** and **multi-employee**.
- **Biweekly payroll rollup** (`docs/prompts/PROMPT_PAYROLL_BIWEEKLY_ROLLUP.md`) — **Aggregated**: one row per employee, **14 day columns** + period total; **approved** timesheets only. Keep endpoints **separate**.

## Context

- **Timesheet statuses:** `draft`, `submitted`, `approved`, `rejected` — there is **no** `closed` on `Timesheet`.
- **Pay period** has `status` (e.g. `open`, `closed`). If the business says **“closed timesheet”**, map it in the ADR to **`PayPeriod.status == closed`**, optionally combined with **`Timesheet.status == approved`** (preset filter `closed_payroll=true` or explicit params).
- **TimeEntry** / **PTOEntry** link to `Timesheet`; filter by `work_date` / `pto_date` in `[start_date, end_date]` and by parent timesheet status (and optional pay period status).
- **Existing payroll** reports are often **approved-only**; this feature intentionally supports **non-approved** data for managers and **self-service** downloads.
- **Read first:** `docs/CONTEXT.md`, `CLAUDE.md`, `.cursor/rules/guardrails.md`. Update **CONTEXT.md**, **TASKS.md**, **DECISIONS.md** (ADR), **CLAUDE.md**.

## Goals

### A. Manager / Admin: multi-employee, status-aware detail report

1. **Endpoint (example):** `GET /api/reports/employee-detail` — single route with role-based behavior (see auth below).
2. **Who may call:** `CurrentManager` or `CurrentAdmin` for **multi-employee** mode.
3. **Employee selection**
   - **One or many:** `employee_id` (single) **xor** `employee_ids` (list). **Do not** treat empty `employee_ids` as “all staff” — that is too easy to misuse.
   - **Explicit “all employees” (optional):** Only if product requires it: separate flag `all_employees=true`, restricted to **`CurrentAdmin`** only, with **max date span** enforced; document in ADR.
   - **Serialization:** Pick **one** style and document in OpenAPI: **repeated** query param (`employee_ids=uuid1&employee_ids=uuid2`) *or* **comma-separated** (`employee_ids=u1,u2`) — note client quirks (e.g. axios array encoding).
4. **Date range:** Required `start_date`, `end_date` (inclusive). **Validate** `start_date <= end_date`. Enforce **maximum span** (e.g. 366 days) and optional **maximum number of employees** per request (e.g. 50) — return **400** with a clear message when exceeded.
5. **Row granularity (required):** **One row per `TimeEntry`** matching filters (not one row per calendar day aggregated). Optional **one row per `PTOEntry`** when `include_pto=true`. State `entry_kind=work|pto` on each row.
6. **Timesheet / period filters**
   - **`timesheet_status`:** Comma-separated or repeated: `draft`, `submitted`, `approved`, `rejected`, or `all`. Default for **this** endpoint: **`all`** (explicitly different from payroll). Payroll-style consumers should pass `approved` only.
   - **`pay_period_status` (optional):** `open`, `closed`, or `all` — filter via join to `PayPeriod`.
   - **Preset (optional):** `closed_payroll=true` — shorthand for “approved timesheets in **closed** pay periods” (define exact SQL in ADR).
7. **Columns (minimum per work row):** `work_date`, `employee_id`, `employee_name`, `client` (name), `location` / site (`site_name`, optional `region`), `site_code` (`JobCode.code`), `job_code_description`, `service_type`, `work_mode`, `hours`, `description`, `is_billable`, `is_overtime`, optional `start_time`, `end_time`, `vehicle_reimbursement_tier`, `timesheet_id`, `timesheet_status`, `pay_period_start`, `pay_period_end`, `period_group`.
8. **PTO rows:** Align columns; use placeholders or `entry_kind=pto` + `pto_type` where work fields do not apply.
9. **Ordering:** `employee_name` (or id), then `date`, then `entry_kind`, then stable tiebreaker (`created_at` or entry id).
10. **Totals (JSON):** `summary` with per-employee subtotals and grand totals (`total_work_hours`, `total_pto_hours`, `total_hours`). **CSV/Excel:** Prefer a **second sheet** (“Summary”) in Excel; for CSV, either append total rows (document format) or export summary as a separate download in a later iteration.
11. **Excel layout (multi-employee):** Prefer **one worksheet per employee** *or* a single sheet with all rows sorted by employee — pick one in ADR (single sheet is simpler for pandas; per-employee sheets are easier for HR).
12. **Download filename:** `Content-Disposition` e.g. `employee_detail_{start}_{end}.xlsx` or include first employee id/name when single-employee.
13. **Performance:** `selectinload` for `client`, `location`, `job_code`, `service_type`, `timesheet`, `timesheet.pay_period`, `employee`; filter on indexed date columns.

### B. Employee: self-service export (own data only)

1. **Recommended pattern:** **Dedicated** `GET /api/reports/my-time-detail` with the **same** query params as the detail report **except** no `employee_id` / `employee_ids` — scope is always `current_user.id`. Reduces risk of employees tampering with query strings.
2. **Alternative:** Same `employee-detail` route: if caller is **not** manager/admin, only allow **no** employee params and force `current_user.id`; **403** if `employee_id` is present and ≠ current user.
3. **Managers using self-download:** When downloading **their own** labor only, they must use **`my-time-detail`** (or the self-scoped branch), **not** the team multi-employee endpoint with only their id — **or** explicitly allow manager to pass **only** their own `employee_id` on the manager endpoint; pick **one** behavior and document it in CLAUDE.md to avoid two conflicting patterns.
4. **Statuses:** Support the same `timesheet_status` and `pay_period_status` filters; default **`all`** for self-export is reasonable so one download covers draft through approved.
5. **Formats:** `json`, `csv`, `excel`.

### C. Security & abuse

- **Authorization matrix**

| Role | Multi-employee `employee-detail` | Self `my-time-detail` |
|------|----------------------------------|------------------------|
| Employee | **403** | **200** — `current_user` only |
| Manager | **200** — any listed employees | **200** — self only |
| Admin | **200** — any listed (+ optional `all_employees`) | **200** — self only |

- **Tests (required):** Employee + **no** employee params → **200** (self). Employee + **another** `employee_id` → **403**. Manager + **two** employee ids → **200** with both. Manager calling **self** endpoint → **200**, only own rows.
- **Audit (optional / follow-up):** Log manager/admin downloads of **draft** data for **other** employees (who, when, range); out of MVP is OK if noted in TASKS.

## Edge cases

- **No rows:** **200**, empty `data`, zeroed `summary`.
- **Entry date vs pay period:** Backend creation rules should keep `work_date` inside the timesheet’s pay period; if legacy bad rows exist, **exclude** or **flag** in `data_quality_warnings` (ADR).

## Tests (`backend/tests/`)

- Manager, two employees, mix of **draft** and **approved**; filter `timesheet_status=draft` excludes approved rows.
- **Pagination:** Out of scope for MVP; if response size is a concern, add follow-up task for streaming or async job.

## Docs to update

| File | Change |
|------|--------|
| `docs/CONTEXT.md` | Manager multi-employee + draft preview; employee self-export; link to biweekly rollup for pay-run grid. |
| `docs/TASKS.md` | Item(s) for implementation + optional audit log. |
| `docs/DECISIONS.md` | ADR: status filters, self vs manager scope, “closed” semantics, row granularity, Excel layout choice. |
| `CLAUDE.md` | Endpoints, examples, `employee_ids` encoding note. |

## Acceptance

- Managers/admins: **one or many** employees, date range, **`timesheet_status` including `draft`** when selected.
- Employees: download **only their** line-level entries; **403** on cross-user access.
- Limits: **max date span** and **max employees** enforced (or admin-only `all_employees` with limits).
- Tests cover auth, filters, and empty result.
- Docs + ADR updated per guardrails.

## Out of scope

- Scheduled/email reports; editing entries from the report; rate limiting implementation details (may be infra) — mention in TASKS if desired.
