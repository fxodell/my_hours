# Prompt: Biweekly payroll rollup report (one row per employee)

**Instructions for implementer:** Add a **dedicated** manager-only report that rolls up **two consecutive weekly pay periods** into **one row per employee** for a biweekly payroll run. Employees are split into Group A / Group B (alternating pay Fridays); weekly timesheets already exist per `PayPeriod` (Sun–Sat, `period_group` A or B).

## Context (from docs and code)

- **CONTEXT.md** — Weekly timesheet submission; staggered A/B groups; payroll export exists but is **per timesheet** (weekly).
- **CLAUDE.md** — `GET /api/reports/payroll` returns one row per **approved** timesheet; optional `pay_period_id` or `start_date`/`end_date` filter; Engage export uses a single `pay_period_id`.
- **Data model** — `Employee.pay_period_group` (`A` | `B`); `PayPeriod` has `period_group`, `start_date`, `end_date` (weekly); `Timesheet` is unique per `(employee_id, pay_period_id)`; only **approved** timesheets should count toward payroll exports (match existing payroll report).
- **DECISIONS.md** — Add an ADR when the rollup rules are finalized (how two weeks are selected, partial weeks, etc.).

## Relationship to other reports (do not merge endpoints)

- **`GET /api/reports/payroll-biweekly` (this prompt)** — **Aggregated**: one row per employee, **14 day columns** + period total + optional bucket columns. For **payroll / pay-run** summaries.
- **Employee detail report** (see `docs/prompts/PROMPT_REPORTS_EMPLOYEE_DETAIL_AND_SELF_EXPORT.md`) — **Line items**: one row per **`TimeEntry`** (and optional PTO row), any status filter, one or many employees. For **audits and draft preview**.
- Keep these **separate** so CSV shapes and auth rules stay clear.

## Problem

Payroll runs **biweekly** (one pay date per group on alternating Fridays), but the app stores **weekly** timesheets. Managers need a **single export** with **one row per employee** for that two-week run, with hours and PTO **summed** across both weeks—not two separate rows per employee. They also need **each calendar day’s hours** across that 14-day window plus a **period total** that reconciles with those days.

## Goals

1. New report endpoint (recommended): e.g. `GET /api/reports/payroll-biweekly` (manager only, same auth as `payroll_report`).
2. **One row per employee** for the selected biweekly run.
3. **Per-day hours (required):** For every calendar day from `biweekly_start` through `biweekly_end` (inclusive, 14 days for two Sun–Sat weeks), include that day’s hours for the employee.
   - **Date semantics:** Use **calendar `date` fields** only (`work_date`, `pto_date`); no timezone conversion unless the product later adds timestamps for entry boundaries.
   - **Source:** `TimeEntry.work_date` + `TimeEntry.hours` from **approved** timesheets whose pay periods fall within the selected biweekly pair; include **PTO** on `PTOEntry.pto_date` in the same day cell unless product prefers PTO only in bucket columns (pick one in ADR; default: **work + PTO combined per day** for a single “hours that day” number). If PTO is **not** in daily cells, document that **`period_total_hours`** = sum(daily work) + **separate** PTO total columns so totals still reconcile.
   - **JSON:** e.g. nested object `hours_by_date: { "2026-03-15": 8.0, "2026-03-16": 0, ... }` or parallel arrays `dates` + `hours` (document chosen shape).
   - **CSV/Excel:** One column per day; use **ISO date** (`YYYY-MM-DD`) as header for clarity and stable sorting, or a documented alias (e.g. `d_2026-03-15`).
4. **Total (required):** Column/field **`period_total_hours`** (name may vary) = sum of all daily hour cells for that employee for the window. It must equal the sum of the 14 daily values (and should align with aggregate `total_work_hours + total_pto_hours` if PTO is included in daily cells).
5. **Aggregate columns (recommended):** Keep rollups consistent with weekly payroll where useful: e.g. `regular_hours`, `overtime_hours`, `total_work_hours`, PTO type buckets, `total_hours`—these should **reconcile** with daily breakdown + documented rules for OT (OT hours can be counted inside the day’s total and also summed in `overtime_hours`).
6. **Identify the two-week window** explicitly in each row: e.g. `biweekly_start`, `biweekly_end`, `period_group`, and optionally `week_1_pay_period_id`, `week_2_pay_period_id` for traceability.
7. **Export formats:** `format=json|csv|excel` consistent with other reports (pandas DataFrame pattern in `reports.py`). Note: CSV/Excel will be **wide** (14+ day columns + totals + employee fields); that is expected for payroll grids.
8. **Download filename:** Set `Content-Disposition` with a descriptive name, e.g. `payroll_biweekly_{period_group}_{biweekly_start}_{biweekly_end}.csv` (sanitize as needed).

## Suggested API shape (implementer may refine)

Pick **one** primary selection mechanism (document in ADR + OpenAPI):

- **Option A (recommended):** Query params `period_group` (`A`|`B`) + `anchor_start_date` — the **Sunday** starting the **first** of the two consecutive weekly `PayPeriod` rows for that group. Server loads exactly those two periods (same `period_group`, consecutive by `start_date`); 400 if either period missing or not consecutive.
- **Option B:** Query params `pay_period_id_1` and `pay_period_id_2` — both must exist, same `period_group`, consecutive weeks; 400 if invalid.
- **Option C:** `start_date` + `end_date` spanning exactly 14 days aligned to two existing weekly periods for a given `period_group` (stricter validation than current payroll date filter).

**Filtering employees:** Include only employees whose `pay_period_group` matches the run’s `period_group` (so Group A rollup does not mix Group B employees).

## Edge cases (must document behavior)

- Employee has **only one** approved timesheet in the pair (second week missing or not approved): include row with **partial** totals vs **exclude** vs **flag** (`weeks_count`, `missing_weeks`) — choose one and document.
- Employee has **no** timesheets in the window: omit row (typical) or include zeros—specify.
- **Non-approved** timesheets: exclude from sums (align with `payroll_report`).
- **Overtime / regular split:** Sum weekly values consistently with current payroll logic.
- **Day with no entries:** Use `0` (or empty string in CSV—prefer `0` for numeric consistency).
- **Multiple time entries same day:** Sum hours for that date (same as summing rows in a day column).
- **Bad data (wrong group / stray entries):** If a timesheet exists for an employee outside their `pay_period_group` (should not happen after fixes) or entries violate pay-period rules, **exclude** those rows from the rollup and optionally emit a **warning** in JSON (`data_quality_warnings`) — document in ADR.

## Backend implementation notes

- **File:** `backend/app/api/reports.py` (new handler + register in `main.py` if needed).
- **Data:** Load approved `Timesheet`s for the two periods + `selectinload` time entries and PTO entries; group by `employee_id`, then bucket by `work_date` / `pto_date`.
- Reuse aggregation logic from `payroll_report` where possible (DRY: shared helper for “totals from one timesheet” then reduce by employee; daily buckets are an additional pass over entries).
- **Tests:** `backend/tests/` — at least one test with two weekly periods, two employees, mixed approval states; assert one row per employee, **daily cells match sum of entries per date**, and **`period_total_hours` equals sum of the 14 daily values**.

## Frontend (optional for MVP)

- If Reports UI exists, add a control for biweekly rollup (group + anchor date or two period pickers). If reports are URL-only for now, document example URLs in CONTEXT/CLAUDE.

## Docs to update

| File | Change |
|------|--------|
| `docs/CONTEXT.md` | Describe biweekly payroll rollup report and how it relates to weekly timesheets and A/B groups. |
| `docs/TASKS.md` | Backlog or Completed item for this feature. |
| `docs/DECISIONS.md` | ADR: how the two-week window is selected; partial-week behavior; employee filter by `pay_period_group`. |
| `CLAUDE.md` | New endpoint under Reports (manager only). |

## Out of scope (unless product asks)

- Changing weekly timesheet workflow to a single 14-day timesheet.
- Automatic alignment to “pay Friday” calendar (manual/admin-defined periods remain source of truth unless specified).
- **Engage export:** Out of scope for MVP **unless** product asks; recommended **follow-up** is a parameter or sibling export that uses the **same two `pay_period_id`s** (or anchor + group) so Engage and the biweekly grid stay aligned.

## Acceptance

- Manager can call the new endpoint and receive **JSON/CSV/Excel** with **at most one row per employee** for the defined two-week run.
- Each row includes **one value per calendar day** in the biweekly window and a **`period_total_hours` (or equivalent) equal to the sum of those daily values**.
- Aggregate columns (if present) reconcile with entry-level data per ADR (work vs PTO vs OT rules).
- Sums match the sum of the corresponding weekly `payroll` rows for the same two periods and employees (where definitions align).
- Invalid period pairs return **400** with a clear message.
- Tests cover the happy path, **daily vs total reconciliation**, and at least one edge case (e.g. partial week, zero day, two entries same day).
- CONTEXT, TASKS, DECISIONS, CLAUDE updated as above.
