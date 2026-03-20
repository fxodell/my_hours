# Prompt: Sort timesheet list by pay period

**Instructions for implementer:** Change the timesheet list API so results are ordered by pay period (most recent period first) instead of by timesheet creation time.

## Context

- **Endpoint:** `GET /api/timesheets` in `backend/app/api/timesheets.py` (`list_timesheets`).
- **Current behavior:** `query.order_by(Timesheet.created_at.desc())` — newest-created timesheet first.
- **Desired behavior:** Sort by pay period so the most recent period appears first (e.g. current or just-ended period at top). Users think in terms of "which period," not "when the timesheet row was created."

## Required change

1. **Backend — `backend/app/api/timesheets.py`**
   - In `list_timesheets()`, the query already joins `PayPeriod` (and `Employee`). Replace the existing `order_by` with ordering by pay period, then timesheet as tiebreaker.
   - Use **`PayPeriod.start_date.desc()`** so the latest period is first. Optionally add **`Timesheet.created_at.desc()`** as a secondary sort so within the same period, newer timesheets come first.
   - Example: `query.order_by(PayPeriod.start_date.desc(), Timesheet.created_at.desc())`.

2. **Docs**
   - **CONTEXT.md** or **CLAUDE.md** — If either describes how timesheets are listed/sorted, update the description to say the list is ordered by pay period (most recent first).
   - **TASKS.md** — Add a Completed item after implementation: "Sort timesheet list by pay period (start_date desc) instead of created_at."
   - **DECISIONS.md** — Optional: add a one-sentence ADR that the timesheet list is sorted by pay period for user-facing relevance.

## Out of scope

- No change to `/timesheets/current`, time entry order, or PTO entry order.
- No frontend changes required; the UI already displays the order returned by the API.

## Acceptance

- `GET /api/timesheets` returns timesheets ordered by pay period start date descending (most recent period first), with a stable tiebreaker (e.g. `created_at.desc()`).
- Existing filters (`pay_period_id`, `employee_id`, `status_filter`) and response shape unchanged.
