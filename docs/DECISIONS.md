# Architecture Decision Records (ADRs)

## Format
Each decision should follow this format:
- **Date**: YYYY-MM-DD
- **Status**: proposed | accepted | deprecated | superseded
- **Context**: What is the issue?
- **Decision**: What was decided?
- **Consequences**: What are the results?

---

<!-- Add ADRs below -->

## ADR-001: Site Request Workflow for New Locations

- **Date**: 2026-03-18
- **Status**: accepted
- **Context**: Employees frequently need to log time against locations (sites) that don't yet exist in the system. Previously, only admins could create locations, causing delays when an employee encountered a missing site during time entry. We needed a self-service path that still gives managers control over what gets created.
- **Decision**: Introduce a **site request** entity (`site_requests` table) with a `pending → approved/rejected` workflow. Employees submit requests (from the Time Entry page inline form or a standalone `/site-requests/new` page). Managers review and approve or reject from `/site-requests`. Approving a request automatically creates a `Location` (and optionally a `JobCode`) and links them back to the request via `created_location_id` / `created_job_code_id`. Duplicate detection prevents creating a location or job code that already exists. Email notifications are sent on submission (to managers) and on approval/rejection (to the requesting employee).
- **Consequences**: Employees are unblocked immediately after submitting a request (they can continue entering time for other sites). Managers retain control over the location catalog. The `site_requests` table provides an audit trail of who requested what and who approved/rejected it. The `/site-requests` routes are accessible to all authenticated users (employees see only their own requests; managers/admins see all).

## ADR-002: Admin-Initiated Password Reset

- **Date**: 2026-03-18
- **Status**: accepted
- **Context**: When employees forget their passwords and cannot use the self-service reset flow (e.g. no email delivery configured, locked out), an admin needs a way to manually set a new password for them. The existing `PATCH /api/employees/{id}` update endpoint could accept a password field, but mixing password resets with general employee updates is unclear and doesn't provide dedicated validation or feedback.
- **Decision**: Add a dedicated admin-only endpoint `POST /api/auth/admin-reset-password` (requires `CurrentAdmin` dependency) that accepts `employee_id` and `new_password`, validates minimum length (6 chars), hashes the password, and clears any outstanding `reset_token`/`reset_token_expires`. The frontend exposes this via a key icon per employee on the admin Employees page, opening a modal with new password + confirm fields.
- **Consequences**: Admins can unblock employees immediately without needing email infrastructure. The endpoint is scoped to admin-only, preventing privilege escalation. Clearing reset tokens on admin reset avoids stale tokens being used after the password is changed. The dedicated endpoint keeps password management separate from general employee CRUD.

## ADR-003: Billing Report Includes Location and Site Code

- **Date**: 2026-03-18
- **Status**: accepted
- **Context**: Invoicing and client reporting need to break down hours by site (location) and AFE/job code.
- **Decision**: The Billing report (`GET /api/reports/billing`) includes **location** (from `Location.site_name`, optionally with `region`) and **site_code** (from `JobCode.code`) on each row; nulls are shown as "Unassigned" and "—" respectively.
- **Consequences**: Managers can export billing data with site and job code detail for invoicing and client breakdown without changing filters or summary behavior.

## ADR-004: Timesheet list sorted by pay period then employee name

- **Date**: 2026-03-18
- **Status**: accepted
- **Context**: The timesheet list was ordered by `created_at.desc()`, which does not match how users think ("which period" vs "when created"); within a period, order was arbitrary for managers.
- **Decision**: `GET /api/timesheets` returns timesheets ordered by `PayPeriod.start_date.desc()` (most recent period first), then `Employee.last_name`, `Employee.first_name` for a stable, scannable list.
- **Consequences**: Current or just-ended period appears at the top; within a period, employees appear alphabetically. No frontend changes required.

## ADR-005: Auth and mutation endpoints use JSON request bodies

- **Date**: 2026-03-19
- **Status**: accepted
- **Context**: Multiple auth endpoints (`change-password`, `reset-password`, `request-reset`, `admin-reset-password`) and the timesheet `reject` endpoint accepted sensitive data (passwords, tokens, rejection reasons) as query parameters. Query params appear in server access logs, browser history, and proxy logs, creating a security risk.
- **Decision**: All auth endpoints and the `reject_timesheet` endpoint now accept parameters via JSON request body using Pydantic schemas (`ChangePasswordRequest`, `RequestResetRequest`, `ResetPasswordRequest`, `AdminResetPasswordRequest`, `TimesheetReject`). Frontend callers updated to send `POST` with `JSON.stringify` body and `Content-Type: application/json`.
- **Consequences**: Breaking API change — any external consumers sending query params must switch to JSON bodies. All current frontend callers have been updated. Passwords and tokens no longer leak to logs.

## ADR-009: Employee detail report and self-service export

- **Date**: 2026-03-19
- **Status**: accepted
- **Context**: Managers need line-level exports for auditing and draft preview across one or many employees, including non-approved timesheets. Employees need to download their own hours without accessing other users' data. Existing payroll reports only cover approved timesheets.
- **Decision**: Two separate endpoints sharing a common `_run_detail_report` helper:
  - `GET /api/reports/employee-detail` — `CurrentManager` required. Accepts `employee_id` (single UUID) xor `employee_ids` (comma-separated UUIDs). Max 50 employees, max 366-day span. Returns one row per `TimeEntry` (and optionally per `PTOEntry` when `include_pto=true`). `entry_kind` column distinguishes `work` vs `pto`. Filters: `timesheet_status` (comma-separated or `all`, default `all`), `pay_period_status` (`open`/`closed`/`all`). JSON includes `summary` (per-employee subtotals) and `grand_total`. Excel includes a Summary sheet.
  - `GET /api/reports/my-time-detail` — `CurrentUser` (any authenticated employee). Same filters but no employee selection params — always scoped to `current_user.id`. Managers use this for their own data, `employee-detail` for others.
  - "Closed timesheet" maps to `pay_period_status=closed` (optionally combined with `timesheet_status=approved` by the caller). No magic preset — callers compose filters explicitly.
  - Row ordering: `employee_name`, `work_date`, `entry_kind`, `description`.
  - Excel layout: single sheet with all rows sorted by employee (simpler for pandas; per-employee sheets deferred).
- **Consequences**: Managers can preview draft work in progress before approval. Employees can self-serve exports without manager involvement. The `employee-detail` endpoint returns 403 for non-managers, preventing cross-user data access. The two endpoints share all query/format logic, keeping the codebase DRY. Pagination is out of scope for MVP (noted in TASKS if needed).

## ADR-007: Biweekly payroll rollup report

- **Date**: 2026-03-19
- **Status**: accepted
- **Context**: Payroll runs biweekly (one pay date per group on alternating Fridays), but the app stores weekly timesheets. Managers need a single export with one row per employee for a two-week run, with hours and PTO summed across both weeks, plus per-day breakdowns for reconciliation.
- **Decision**: New endpoint `GET /api/reports/payroll-biweekly` (manager only) using **Option A** selection: `period_group` (A|B) + `anchor_start_date` (the Sunday starting the first week). Server loads exactly two consecutive weekly `PayPeriod` rows for that group; returns 400 if either is missing or they're not consecutive. One row per employee whose `pay_period_group` matches. Each row includes: per-day hours (`hours_by_date` dict in JSON, one column per day in CSV/Excel) combining work + PTO for each calendar day; `period_total_hours` equal to sum of daily values; aggregate columns (`regular_hours`, `overtime_hours`, `total_work_hours`, PTO type buckets, `total_hours`); `weeks_count` and `missing_weeks` for partial-week flagging. Only approved timesheets are included. Employees with no approved timesheets in the window are omitted. Employees with only one approved week are included with partial totals and `missing_weeks` populated.
- **Consequences**: Managers can export biweekly payroll grids in JSON/CSV/Excel. Daily values reconcile with `period_total_hours`. Aggregate columns reconcile with the sum of the two corresponding weekly `payroll` report rows. Wide CSV/Excel format (14+ day columns) is expected for payroll grids. The endpoint validates consecutive periods strictly, preventing accidental misalignment.

## ADR-008: Pay period group enforcement on timesheet creation

- **Date**: 2026-03-19
- **Status**: accepted
- **Context**: Multiple endpoints (`GET /api/timesheets/current`, `GET /api/timesheets/for-period/{id}`, `POST /api/timesheets`, `GET /api/pay-periods/current`, `GET /api/pay-periods/recent`) did not filter by the employee's `pay_period_group`. This allowed Group A employees to see Group B pay periods in the UI and accidentally create timesheets in the wrong group, producing overlapping timesheets.
- **Decision**: All pay period lookup endpoints used by employees (`/current`, `/recent`) now filter `WHERE period_group = employee.pay_period_group`. Timesheet creation endpoints (`/for-period/{id}`, `POST /timesheets`) validate that the target pay period's group matches the employee's group (or the target employee's group for admin-on-behalf creation), returning 400 if mismatched.
- **Consequences**: Employees only see and can create timesheets in their assigned group's pay periods. Cross-group timesheet creation is blocked at the API level. Existing cross-group orphan timesheets were cleaned up manually. Admin CRUD endpoints for pay periods remain unfiltered (admins manage all groups).

## ADR-006: Employee list response scoped by role

- **Date**: 2026-03-19
- **Status**: accepted
- **Context**: The `GET /api/employees` and `GET /api/employees/{id}` endpoints returned full employee details — including `hourly_rate`, `engage_employee_id`, and `quickbooks_employee_id` — to any authenticated user. Regular employees could see every other employee's pay rate, which is a privacy concern.
- **Decision**: The employee list and detail endpoints now return different response schemas based on the caller's role. Managers and admins receive `EmployeeResponse` (full details including `hourly_rate` and integration IDs). Regular employees receive `EmployeeSummaryResponse` (basic info only: name, email, role, group, active status). The endpoint uses `JSONResponse` with conditional schema serialization rather than a static `response_model`.
- **Consequences**: Employee pay rates are no longer visible to non-manager users. The endpoint loses automatic OpenAPI response schema documentation (trade-off for role-conditional responses). Frontend code that relies on `hourly_rate` in non-admin contexts will see `undefined` — currently only the admin Employees page uses this field, which is correct.

## ADR-010: Weekly Billing Weeks Within Bi-Weekly Timesheets

- **Date**: 2026-03-24
- **Status**: accepted
- **Context**: Timesheets cover bi-weekly pay periods, but billing and invoicing operate on a weekly cycle (Monday-Sunday). Managers need to approve and lock entries on a per-week basis for billing purposes, independently of the overall timesheet approval status. Without this, a single bi-weekly timesheet could not reflect that one week's billing is finalized while the other is still open.
- **Decision**: Introduce a `BillingWeek` model (`billing_weeks` table) with a many-to-one relationship to `Timesheet`. Each bi-weekly timesheet automatically gets two billing weeks (Monday-Sunday) created via `_ensure_billing_weeks()` on first access. Billing weeks have their own status workflow: `open → submitted → approved → billed` (with `reopened` as a return state). Manager-only endpoints handle status transitions. When a billing week reaches `approved` or `billed` status, all time entry and PTO entry mutations for dates within that week are blocked (returns 403 via `_is_date_locked_for_billing_week()` helper). The billing week workflow is independent of the timesheet-level submit/approve/reject workflow.
- **Consequences**: Managers can finalize billing on a weekly cadence even though payroll runs bi-weekly. Entry locking prevents employees from modifying already-billed work. The two-level workflow (timesheet status + billing week status) adds complexity but reflects the real business process. Auto-creation ensures billing weeks always exist without manual setup. Cascade delete on the timesheet FK ensures billing weeks are cleaned up if a timesheet is deleted.

## ADR-011: Super Admin Role and Cross-Company Access

- **Date**: 2026-03-24
- **Status**: accepted
- **Context**: With multi-tenant company isolation, each admin is scoped to their own company. System operators who manage multiple companies (e.g. the platform owner) need a way to view and manage data across companies, create new companies, and perform cross-company administrative actions like password resets.
- **Decision**: Add an `is_super_admin` boolean to the Employee model (separate from `is_admin`). Super admins gain: (1) Company CRUD via `POST/GET/PATCH/DELETE /api/companies`; (2) Cross-company data access via optional `company_id` query parameter on list/report endpoints, resolved by `resolve_company_id()` in deps.py — non-super-admins have this parameter silently ignored; (3) Cross-company password reset via the existing admin-reset-password endpoint; (4) Frontend `CompanyContext` and `CompanySelector` component allowing super-admins to switch company views. A new `SuperAdminRoute` guard protects the `/companies` frontend route. The `CurrentSuperAdmin` dependency in deps.py enforces backend access.
- **Consequences**: Platform operators can manage all companies from a single account. The `resolve_company_id()` pattern keeps multi-tenant filtering centralized — endpoints don't need individual company-switching logic. Regular admins and below are completely unaffected; the `company_id` parameter is ignored for them. Super admin is opt-in (default false) and cannot be self-assigned through the API — it must be set directly or by another super admin.
