# Project Context

## Overview

MyHours is a mobile-first employee timesheet system that replaces spreadsheet-based payroll tracking with role-based web workflows and exportable reports.

Current implementation includes:
- **Multi-tenant company isolation:** Each company's data (employees, clients, timesheets, pay periods, etc.) is fully isolated via `company_id` foreign keys on all business entities
- Employee time and PTO entry by pay period
- Timesheet list ordered by pay period (newest first), then by employee name (last name, first name) for stable, scannable manager view
- Timesheet workflow: `draft -> submitted -> approved/rejected`, with manager/admin reopen
- Billing workflow inside each weekly timesheet: one Monday-Sunday billing week auto-created per timesheet (`open -> submitted -> approved -> billed`, with manager reopen at any stage). Entries in approved/billed weeks are locked from employee add/edit/delete (returns 403).
- Role-based access controls for employee, manager, admin, and super-admin use cases
- Manager reporting exports (payroll, employee detail with draft support, billing report by client, location, site code, employee, service type; hours by employee; hours by job code)
- Employee self-service export (`/api/reports/my-time-detail`) for downloading own time entries (all statuses)
- Weekly Monday-Sunday pay period groups (A/B)
- Password change + password reset request/reset flows
- Company CRUD for super-admins (`/api/companies`)

## Current Architecture

### Backend
- **Framework:** FastAPI (Python 3.12)
- **Data layer:** SQLAlchemy 2.x + Alembic
- **Database:** PostgreSQL in runtime environments
- **AuthN/AuthZ:** JWT bearer token auth, role checks via dependency injection
- **API base path:** `/api/*`
- **Docs/OpenAPI:** `/api/docs`, `/api/redoc`, `/api/openapi.json`
- **Health endpoint:** `/api/health`

### Frontend
- **Framework:** React 18 + TypeScript + Vite
- **State/data:** TanStack Query + React Context + React Hook Form
- **Styling:** Tailwind CSS
- **PWA:** `vite-plugin-pwa` with runtime caching for API/font assets
- **Route guards:** `ProtectedRoute`, `ManagerRoute`, `AdminRoute`, `SuperAdminRoute` — all check `isLoading` before redirecting to prevent premature navigation while auth state resolves
- **Reusable components:** `SearchableSelect` (dropdown with search/filter, keyboard navigation), `Layout` (header + two-row bottom nav for mobile), `CompanySelector` (super-admin company switcher dropdown)
- **API layer:** `fetchApi` wrapper in `services/api.ts` handles JWT tokens, auto-redirects to `/login` on 401, returns typed responses; `fetchApiBlob` for report file downloads
- **Company context:** `CompanyContext` provides `useCompany()` hook for super-admin company switching; `companyParam` is appended to API calls when a super-admin has selected a different company

### Database Engine Pattern

The backend uses two SQLAlchemy engines from `backend/app/core/database.py`:
- **Async engine (`asyncpg`)** for request handling via `get_db()`
- **Sync engine (`psycopg2`)** for migrations/scripts

### Runtime and Deployment Options
- Local development through `make` targets (`dev`, `dev-frontend`, `dev-all`)
- Local Docker Compose stack (`db`, `backend`, `frontend`)
- Production deployment details are partially documented in project guidance and should be consolidated over time
- Production database backup: nightly `pg_dump` at 02:15 with 90-day retention and a 02:45 health audit, scheduled via `/etc/cron.d/myhours-backup`. The cron file is version-controlled at `scripts/cron/myhours-backup`, installed by `scripts/install-backup-cron.sh`, and auto-synced by `scripts/production-restart-backend.sh` on every deploy. Restore runbook: `docs/BACKUP_RESTORE.md`

## Key Directories

- `backend/app/main.py` - FastAPI app configuration and router registration
- `backend/app/api/` - Route handlers (`auth`, `timesheets`, `reports`, `site_requests`, admin CRUD)
- `backend/app/api/deps.py` - Auth and role dependency aliases (`CurrentUser`, `CurrentManager`, `CurrentAdmin`, `CurrentSuperAdmin`), `resolve_company_id()` for multi-tenant scope
- `backend/app/api/companies.py` - Company CRUD (super-admin only)
- `backend/app/models/company.py` - Company model (name, slug, is_active)
- `backend/app/models/billing_week.py` - BillingWeek model (weekly billing status within timesheets)
- `backend/app/models/` - SQLAlchemy models + mixins
- `backend/app/schemas/` - Pydantic schemas
- `backend/scripts/seed_data.py` - Seed reference data + initial admin
- `backend/scripts/import_locations.py` - Location/job-code import utility
- `frontend/src/App.tsx` - Frontend route map and access guards
- `backend/app/models/site_request.py` - SiteRequest model (employee → manager approval → Location/JobCode creation)
- `frontend/src/pages/` - User, manager, and admin page components
- `frontend/src/pages/SiteRequests.tsx` - Site request list with manager approve/reject actions
- `frontend/src/pages/SiteRequestForm.tsx` - Standalone new site request form
- `frontend/src/pages/Companies.tsx` - Company management (super-admin only)
- `frontend/src/contexts/CompanyContext.tsx` - Company selection context for super-admin cross-company access
- `frontend/src/components/CompanySelector.tsx` - Company switcher dropdown (renders only for super-admins)
- `frontend/src/types/reports.ts` - Typed JSON response interfaces for report previews
- `frontend/src/services/api.ts` - Frontend API wrapper and auth token handling

## Core Domain Workflow

Timesheet lifecycle:
1. Employee creates/edits a timesheet in `draft` (or edits after `rejected`)
2. Employee submits timesheet (`submitted`) or a manager/admin submits on the employee's behalf when needed
3. Manager/admin approves (`approved`) or rejects (`rejected`) with reason
4. Manager/admin may reopen submitted/approved timesheets back to `draft`
5. Submission attribution is stored on the timesheet (`submitted_by`) for auditability

Time and PTO entry editability:
- `draft` and `rejected` timesheets are editable (add/update/delete entries)
- `submitted` and `approved` timesheets are read-only in the employee UI; edit/add/delete controls are hidden and a status-specific banner is shown
- Both time entry and PTO entry dates can be entered for any day within the active pay period bounds (past dates included), while dates outside the pay period are rejected by backend validation
- Entries in a billing week marked `approved` or `billed` are locked from employee add/edit/delete operations for both time and PTO (returns 403 via `_is_date_locked_for_billing_week()` helper)
- A billing week is auto-created when a timesheet is first retrieved or created (`_ensure_billing_weeks()`), matching the weekly Monday-Sunday pay period
- Adding a time or PTO entry to a `rejected` timesheet auto-resets it to `draft`
- Frontend entry forms (`TimeEntry.tsx`, `PTOEntry.tsx`) accept a `?timesheet=<id>` query parameter to target a specific timesheet; `TimesheetDetail.tsx` passes this when linking to "Add Time" / "Add PTO"
- Shared editability helpers in `frontend/src/timesheetStatus.ts`: `isTimesheetEditable()`, `isTimesheetReadOnly()`, `getEntryDateMax()`
- The `bonus_eligible` time-entry field has been removed from UI and API payloads; database schema no longer stores per-entry bonus eligibility
- **Time entry create validation:** `description` is required (non-empty after trim) on create; `job_code_id` is required on create when the selected location has one or more active job codes (backend returns 400, frontend validates before submit). These rules apply to create only, not edit.

Site request workflow (API/table `site_requests`; user-facing **location request** in the app):
1. Employee needs a location that doesn't exist yet — submits a **location request** (not a location row directly)
2. Requests are stored in the `site_requests` table with status `pending`
3. Submission paths:
   - **Inline from Time Entry:** On the Add Time page, after selecting a client, if the needed location isn't listed the employee clicks "Can't find your site? Request a new one" and fills out an inline form (site name, region, optional AFE/job code + description, notes). The client is pre-filled from the current selection.
   - **Standalone form:** Navigate to `/site-requests/new` (linked from the Site Requests page)
4. On submission, managers are notified by email (logged in dev mode)
5. Managers (or admins) review pending requests at `/site-requests`, where they see all requests with status filters (pending, approved, rejected)
6. **Approve:** Creates a new `Location` for the client (with site name and region). If AFE/job code info was provided, also creates a `JobCode` on that location. The request is updated with `status=approved`, `reviewed_by`, `reviewed_at`, `created_location_id`, and optionally `created_job_code_id`. Duplicate locations/job codes are detected and reused. The requesting employee is notified by email. The frontend invalidates `locations` and `jobCodes` query caches on approve so new locations appear immediately in entry form dropdowns.
7. **Reject:** Manager provides a rejection reason. Request is set to `rejected` with `rejection_reason`. The employee is notified by email.
8. Employees can only view their own requests; managers/admins see all requests.

Access model (all roles are company-scoped):
- **Employee:** own timesheets and entries; create and view own site requests; employee list returns summary response (no hourly_rate or integration IDs)
- **Manager:** approvals, reports, broader timesheet visibility; approve/reject all site requests; employee list returns full response (includes hourly_rate) — all within own company only
- **Admin:** manager capabilities plus employee/client/service/location/pay-period administration; can reset passwords for employees in same company only via `POST /api/auth/admin-reset-password`
- **Super Admin:** (`is_super_admin=true`) all admin capabilities plus cross-company access: company CRUD (`/api/companies`), can reset passwords for any employee in any company, can create employees in other companies

Multi-tenant isolation:
- Every business entity (Employee, Client, ServiceType, PayPeriod, Timesheet, Location, JobCode, SiteRequest) has a `company_id` FK
- All list/get/update/delete endpoints filter by `current_user.company_id`, returning 404 for cross-company access attempts
- Employee `email` remains globally unique (login by email alone works without company context)
- Tenant-scoped unique constraints: `(company_id, name)` for clients/service types, `(company_id, period_group, start_date)` for pay periods
- JWT tokens include `company_id` claim
- Admin password reset is scoped to same company (super-admin can reset any)

Soft delete pattern:
- Employees, Locations, JobCodes, Clients, and ServiceTypes use soft delete (set `is_active = false`) rather than hard delete
- `DELETE` endpoints for these resources deactivate the record; list endpoints filter `active_only=true` by default

Pay period model:
- Employees are assigned to Group A or Group B
- Pay periods are 7-day Monday-Sunday weeks generated per group
- Pay period endpoints (`/current`, `/recent`) and timesheet creation endpoints filter by the employee's `pay_period_group` to prevent cross-group timesheet creation

## Development Setup (Current)

1. Install prerequisites: Python 3.12+, Node.js 20+, Docker
2. Start database: `make db-start`
3. Install backend deps: `make install`
4. Install frontend deps: `make install-frontend`
5. Apply migrations: `make migrate`
6. Seed baseline data: `make seed`
7. Run backend API: `make dev` (port `8000`)
8. Run frontend app: `make dev-frontend` (port `3000`)

## Testing State

- Backend tests currently run against in-memory SQLite (`backend/tests/conftest.py`)
- Test coverage includes: auth, health, time entry CRUD (past-day, out-of-period, post-submit blocking), PTO entry CRUD (date validation, post-submit blocking), employee detail reports, site requests, billing weeks (auto-creation, entry locking), multi-tenant isolation (cross-company access denied for employees/clients/timesheets/reports/password-reset, company CRUD permissions)
- Key test files: `test_billing_weeks.py`, `test_multi_tenant.py`, `test_timesheet_lifecycle.py`, `test_admin_crud.py`, `test_report_exports.py`, `test_site_requests.py`
- Engine and fixtures are function-scoped: each test gets a fresh database

## Frontend Patterns and Conventions

- **Entry forms** (`TimeEntry.tsx`, `TimeEntryEdit.tsx`, `PTOEntry.tsx`, `PTOEntryEdit.tsx`) use cascading selects (Client → Location → Job Code) with `useEffect` + `setValue` resets on parent change; time entry forms use mutually exclusive **Duration** modes — **Start & end time** (hours computed from the span) or **Hours worked** (tapped values), not both at once
- **Locations** may store optional `site_code`, `latitude`, and `longitude`; `GET /api/locations` embeds active **job codes** per location. Employees use **Location lookup** (`/location-lookup`) to browse by client and open **Google Maps** directions from coordinates. Admins edit GPS/site code on the Locations admin page. Bulk sync from `data/ApacheSiteListGPS.csv` (including optional `job_codes` column): `python scripts/import_apache_site_gps.py` from `backend/`
- **Pay period selector** in entry forms shows "Current" badge based on date comparison (`start_date <= today <= end_date`) and grace-period countdown for closed periods
- **Report preview + download** — each report section on the Reports page has both a **Preview** button (fetches `format=json` via TanStack Query on demand) and a **Download** button (CSV/Excel blob). Preview renders summary stats and a scrollable table inline; the Engage export remains download-only. Typed JSON response interfaces live in `frontend/src/types/reports.ts` (`PayrollReport`, `BillingReport`, `BiweeklyReport`, `DetailReport`, `HoursByJobCodeReport`, `HoursByEmployeeReport`). Preview queries use `enabled: false` until the user clicks Preview to avoid unnecessary API calls
- **Profile page** auto-dismisses success messages after 5 seconds
- **Validation approach:** Backend is the source of truth for all business rules; frontend provides UX-level validation (required fields, date ranges) but does not duplicate backend logic

## Known Gaps / Follow-ups

- Email notifications are currently logged in development mode rather than sent through an SMTP/provider integration
- Password reset tokens are gated behind `settings.debug` for logging but no production email delivery yet
