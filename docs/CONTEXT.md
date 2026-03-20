# Project Context

## Overview

MyHours is a mobile-first employee timesheet system that replaces spreadsheet-based payroll tracking with role-based web workflows and exportable reports.

Current implementation includes:
- Employee time and PTO entry by pay period
- Timesheet list ordered by pay period (newest first), then by employee name (last name, first name) for stable, scannable manager view
- Timesheet workflow: `draft -> submitted -> approved/rejected`, with manager/admin reopen
- Role-based access controls for employee, manager, and admin use cases
- Manager reporting exports (payroll, biweekly payroll rollup, employee detail with draft support, billing report by client, location, site code, employee, service type; hours by employee; hours by job code)
- Employee self-service export (`/api/reports/my-time-detail`) for downloading own time entries (all statuses)
- Staggered bi-weekly pay period groups (A/B)
- Password change + password reset request/reset flows

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
- **Route guards:** `ProtectedRoute`, `ManagerRoute`, `AdminRoute` — all three check `isLoading` before redirecting to prevent premature navigation while auth state resolves
- **Reusable components:** `SearchableSelect` (dropdown with search/filter, keyboard navigation), `Layout` (header + bottom nav for mobile)
- **API layer:** `fetchApi` wrapper in `services/api.ts` handles JWT tokens, auto-redirects to `/login` on 401, returns typed responses; `fetchApiBlob` for report file downloads

### Database Engine Pattern

The backend uses two SQLAlchemy engines from `backend/app/core/database.py`:
- **Async engine (`asyncpg`)** for request handling via `get_db()`
- **Sync engine (`psycopg2`)** for migrations/scripts

### Runtime and Deployment Options
- Local development through `make` targets (`dev`, `dev-frontend`, `dev-all`)
- Local Docker Compose stack (`db`, `backend`, `frontend`)
- Production deployment details are partially documented in project guidance and should be consolidated over time

## Key Directories

- `backend/app/main.py` - FastAPI app configuration and router registration
- `backend/app/api/` - Route handlers (`auth`, `timesheets`, `reports`, `site_requests`, admin CRUD)
- `backend/app/api/deps.py` - Auth and role dependency aliases (`CurrentUser`, `CurrentManager`, `CurrentAdmin`)
- `backend/app/models/` - SQLAlchemy models + mixins
- `backend/app/schemas/` - Pydantic schemas
- `backend/scripts/seed_data.py` - Seed reference data + initial admin
- `backend/scripts/import_locations.py` - Location/job-code import utility
- `frontend/src/App.tsx` - Frontend route map and access guards
- `backend/app/models/site_request.py` - SiteRequest model (employee → manager approval → Location/JobCode creation)
- `frontend/src/pages/` - User, manager, and admin page components
- `frontend/src/pages/SiteRequests.tsx` - Site request list with manager approve/reject actions
- `frontend/src/pages/SiteRequestForm.tsx` - Standalone new site request form
- `frontend/src/services/api.ts` - Frontend API wrapper and auth token handling

## Core Domain Workflow

Timesheet lifecycle:
1. Employee creates/edits a timesheet in `draft` (or edits after `rejected`)
2. Employee submits timesheet (`submitted`)
3. Manager/admin approves (`approved`) or rejects (`rejected`) with reason
4. Manager/admin may reopen submitted/approved timesheets back to `draft`

Time and PTO entry editability:
- `draft` and `rejected` timesheets are editable (add/update/delete entries)
- `submitted` and `approved` timesheets are read-only in the employee UI; edit/add/delete controls are hidden and a status-specific banner is shown
- Both time entry and PTO entry dates can be entered for any day within the active pay period bounds (past dates included), while dates outside the pay period are rejected by backend validation
- Adding a time or PTO entry to a `rejected` timesheet auto-resets it to `draft`
- Frontend entry forms (`TimeEntry.tsx`, `PTOEntry.tsx`) accept a `?timesheet=<id>` query parameter to target a specific timesheet; `TimesheetDetail.tsx` passes this when linking to "Add Time" / "Add PTO"
- Shared editability helpers in `frontend/src/timesheetStatus.ts`: `isTimesheetEditable()`, `isTimesheetReadOnly()`, `getEntryDateMax()`
- The `bonus_eligible` time-entry field has been removed from UI and API payloads; database schema no longer stores per-entry bonus eligibility

Site request workflow:
1. Employee needs a location that doesn't exist yet — submits a **site request** (not a location directly)
2. Requests are stored in the `site_requests` table with status `pending`
3. Submission paths:
   - **Inline from Time Entry:** On the Add Time page, after selecting a client, if the needed location isn't listed the employee clicks "Can't find your site? Request a new one" and fills out an inline form (site name, region, optional AFE/job code + description, notes). The client is pre-filled from the current selection.
   - **Standalone form:** Navigate to `/site-requests/new` (linked from the Site Requests page)
4. On submission, managers are notified by email (logged in dev mode)
5. Managers (or admins) review pending requests at `/site-requests`, where they see all requests with status filters (pending, approved, rejected)
6. **Approve:** Creates a new `Location` for the client (with site name and region). If AFE/job code info was provided, also creates a `JobCode` on that location. The request is updated with `status=approved`, `reviewed_by`, `reviewed_at`, `created_location_id`, and optionally `created_job_code_id`. Duplicate locations/job codes are detected and reused. The requesting employee is notified by email.
7. **Reject:** Manager provides a rejection reason. Request is set to `rejected` with `rejection_reason`. The employee is notified by email.
8. Employees can only view their own requests; managers/admins see all requests.

Access model:
- **Employee:** own timesheets and entries; create and view own site requests; employee list returns summary response (no hourly_rate or integration IDs)
- **Manager:** approvals, reports, broader timesheet visibility; approve/reject all site requests; employee list returns full response (includes hourly_rate)
- **Admin:** manager capabilities plus employee/client/service/location/pay-period administration; can reset any employee's password via `POST /api/auth/admin-reset-password` (from the Employees page, key icon per employee opens a modal)

Soft delete pattern:
- Employees, Locations, JobCodes, Clients, and ServiceTypes use soft delete (set `is_active = false`) rather than hard delete
- `DELETE` endpoints for these resources deactivate the record; list endpoints filter `active_only=true` by default

Pay period model:
- Employees are assigned to Group A or Group B
- Pay periods are generated by group on alternating two-week cycles
- Pay period endpoints (`/current`, `/recent`) and timesheet creation endpoints filter by the employee's `pay_period_group` to prevent cross-group timesheet creation
- Biweekly payroll rollup report (`GET /api/reports/payroll-biweekly`) rolls up two consecutive weekly pay periods into one row per employee with per-day hours and aggregate totals; employees are filtered to the selected `period_group`

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
- Test coverage includes: auth, health, time entry CRUD (past-day, out-of-period, post-submit blocking), PTO entry CRUD (date validation, post-submit blocking), employee detail reports, biweekly payroll reports, site requests
- Engine and fixtures are function-scoped: each test gets a fresh database — all 42 tests pass together without isolation issues

## Frontend Patterns and Conventions

- **Entry forms** (`TimeEntry.tsx`, `TimeEntryEdit.tsx`, `PTOEntry.tsx`, `PTOEntryEdit.tsx`) use cascading selects (Client → Location → Job Code) with `useEffect` + `setValue` resets on parent change
- **Pay period selector** in entry forms shows "Current" badge based on date comparison (`start_date <= today <= end_date`) and grace-period countdown for closed periods
- **Report downloads** use concurrent download tracking (`activeDownloads` Set) with date range validation (`startDate <= endDate`) before fetching
- **Profile page** auto-dismisses success messages after 5 seconds
- **Validation approach:** Backend is the source of truth for all business rules; frontend provides UX-level validation (required fields, date ranges) but does not duplicate backend logic

## Known Gaps / Follow-ups

- Email notifications are currently logged in development mode rather than sent through an SMTP/provider integration
- Password reset tokens are gated behind `settings.debug` for logging but no production email delivery yet
