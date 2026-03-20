# Prompt: Add Location and Site Code to Billing Report

**Instructions for implementer:** Read the docs and code referenced below, then add **location** (site) and **site code** (job code) to the Billing report so invoicing and client reporting can break down hours by site and AFE/job code.

## Context (from docs)

- **CONTEXT.md** — MyHours is a timesheet system; manager reports include payroll, billing, hours-by-employee, hours-by-job-code. Data model: Client → Location → JobCode; TimeEntry has `client_id`, `location_id`, `job_code_id`, `service_type_id`.
- **DECISIONS.md** — ADRs describe site request workflow and admin password reset; no ADR yet for report column changes.
- **TASKS.md** — Billing report is under Completed; this is an enhancement to add columns.

## Current Billing Report

- **Endpoint:** `GET /api/reports/billing` (manager only). Query params: `client_id`, `start_date`, `end_date`, `format` (json, csv, excel).
- **Location:** `backend/app/api/reports.py` — `billing_report()` (around line 125).
- **Current row fields:** `date`, `client`, `employee`, `service_type`, `hours`, `work_mode`, `description`.
- **Data source:** Approved, billable `TimeEntry` rows with `selectinload(TimeEntry.client)`, `selectinload(TimeEntry.service_type)`; **location** and **job_code** are not loaded or output.

## Required Changes

1. **Backend — include location and job code on each row**
   - In `billing_report()`, add `selectinload(TimeEntry.location)` and `selectinload(TimeEntry.job_code)` to the query options.
   - For each entry, add to the report row:
     - **location** — display name for the site: use `entry.location.site_name` (and optionally `entry.location.region` if you want e.g. "Site Name (Region)" or a second column). If `entry.location` is None, use a placeholder such as `"Unassigned"` or `"—"`.
     - **site_code** (or **job_code**) — use `entry.job_code.code` when present (JobCode.code is the AFE/site code). If `entry.job_code` is None, use a placeholder such as `""`, `"N/A"`, or `"—"`.
   - Ensure these fields appear in the same order in JSON, CSV, and Excel outputs (e.g. add after `client` or after `service_type` so the report reads logically: client → location → site code → service type → hours, etc.).

2. **Naming**
   - Use consistent column names across formats, e.g. **Location** (or **Site**) and **Site Code** (or **Job Code**) in CSV/Excel headers and the same keys in JSON.

3. **Docs**
   - **CONTEXT.md** — In the bullet that lists manager reporting, add that the billing report includes location and site code (e.g. "billing report by client, location, site code, employee, service type").
   - **TASKS.md** — Add a Completed item: "Add location and site code columns to Billing report" (after implementation), or a Current Sprint/Backlog item if this prompt is used as a task spec.
   - **DECISIONS.md** — Optional: add a short ADR that the Billing report includes location and job code for invoicing and client breakdown (one sentence is enough).

## Files to Touch

| File | Change |
|------|--------|
| `backend/app/api/reports.py` | In `billing_report()`, add selectinload for `TimeEntry.location` and `TimeEntry.job_code`; add `location` and `site_code` (or `job_code`) to each report row and to DataFrame/export. |
| `docs/CONTEXT.md` | State that the billing report includes location and site code. |
| `docs/TASKS.md` | Add task for this enhancement (Sprint/Backlog or Completed after done). |
| `docs/DECISIONS.md` | Optional ADR for billing report columns. |

## Models (reference)

- **TimeEntry** (`backend/app/models/time_entry.py`): `location_id`, `job_code_id`; relationships `location`, `job_code`.
- **Location** (`backend/app/models/location.py`): `site_name`, `region`.
- **JobCode** (`backend/app/models/job_code.py`): `code` (AFE/site code), `description`.

## Out of Scope

- No change to payroll, hours-by-employee, or Engage export reports unless specifically requested.
- No frontend UI change required for the report (managers already use the existing Reports page and export); only backend and docs.

## Acceptance

- Billing report JSON includes `location` and `site_code` (or `job_code`) per row.
- Billing report CSV and Excel include **Location** and **Site Code** (or **Job Code**) columns with correct values or placeholders when null.
- Existing filters (`client_id`, `start_date`, `end_date`) and summary-by-client behavior unchanged.
