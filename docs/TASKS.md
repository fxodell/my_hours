# Tasks

## Current Sprint
- [ ] Document role-based test scenarios for employee/manager/admin flows
- [ ] Add API integration tests for timesheet submit/approve/reject/reopen lifecycle
- [ ] Add API integration tests for report export endpoints (CSV and Excel)
- [ ] Add tests for admin CRUD endpoints (clients, service types, employees, locations, pay periods)
- [x] Migrate Clients and ServiceTypes from hard delete to soft delete (add `is_active` flag, matching Employee/Location/JobCode pattern)
- [x] Add pagination (limit/offset) to client and location list endpoints
- [x] Fix test infrastructure: replace session-scoped engine with function-scoped transactions to avoid unique constraint collisions

## Backlog
- [ ] Replace development email logger with configurable SMTP/provider implementation
- [ ] Add QuickBooks export/invoicing integration path
- [ ] Add audit logging for status transitions and sensitive admin actions
- [ ] Add stronger password policy and optional MFA support
- [ ] Add seed/import idempotency tests and data validation checks
- [ ] Improve dashboard analytics and manager review queue UX
- [ ] Add CI pipeline for lint/test/build checks
- [ ] Add aria-labels to icon-only buttons across frontend (edit, delete, status actions)
- [ ] Add error boundaries around modal dialogs (Approvals, TimesheetDetail)
- [ ] Verify PWA icon files exist in public directory (pwa-192x192.png, pwa-512x512.png)

## Completed
- [x] Fix `TimeEntry.tsx` pay period selector: compute `isCurrentPeriod` from dates instead of hardcoded `true` (matching `PTOEntry.tsx` behavior)
- [x] Fix `Profile.tsx` success message: auto-dismiss after 5 seconds instead of persisting forever
- [x] Fix `SearchableSelect.tsx` keyboard navigation: guard ArrowDown against empty filtered list
- [x] Fix `ManagerRoute`/`AdminRoute` loading state: add `isLoading` check to prevent premature redirects before auth resolves
- [x] Add validators to `TimeEntryUpdate` and `PTOEntryUpdate` schemas (hours range, work_mode, pto_type)
- [x] Fix password reset token info leak: merge invalid/expired error messages into single response
- [x] Gate reset token debug logging behind `settings.debug`
- [x] Add date range validation (`startDate <= endDate`) to Reports download functions
- [x] Fix employee detail report sort key: use structural work-context fields instead of description
- [x] Add `selectinload(Timesheet.pay_period)` to timesheets list query
- [x] Remove unused `selectinload` import from `locations.py`
- [x] Add employee detail report (`GET /api/reports/employee-detail`): line-level rows per entry, multi-employee, status-aware (including draft), date range, JSON/CSV/Excel with Summary sheet
- [x] Add self-service export (`GET /api/reports/my-time-detail`): employees download own entries, all statuses, scoped to current user only
- [x] Add biweekly payroll rollup report (`GET /api/reports/payroll-biweekly`): one row per employee for two consecutive weekly pay periods, with per-day hours, aggregate totals, and JSON/CSV/Excel export
- [x] Fix cross-group timesheet bug: pay period endpoints and timesheet creation now filter by employee's `pay_period_group`
- [x] Fix Docker backend healthcheck path to use `/api/health` instead of `/health`
- [x] Fix health test to use `/api/health` endpoint path
- [x] Fix all auth endpoints (`change-password`, `reset-password`, `request-reset`, `admin-reset-password`): move params from query strings to JSON request bodies, add 6-char minimum validation on `change-password`
- [x] Fix `TimeEntryEdit` to fetch the timesheet's pay period instead of current pay period (wrong date constraints on past-period entries)
- [x] Standardize PTO entry editability error codes from 400 to 403 (matching time entry operations)
- [x] Remove unused `asyncio` import from `timesheets.py`
- [x] Make `SECRET_KEY` required in production (raises on startup if not set and `DEBUG=false`); warns in dev mode when using insecure default
- [x] Fix `reject_timesheet` endpoint: move `rejection_reason` from query param to JSON body using `TimesheetReject` schema; stop incorrectly setting `approved_by` on rejection
- [x] Fix `TimeEntryEdit` cascading select: reset location/job code when client changes (matching TimeEntry create form behavior)
- [x] Fix `rejectTimesheet` frontend call: send rejection reason as JSON body instead of query param
- [x] Hide `hourly_rate` and integration IDs from non-manager employees: `GET /api/employees` and `GET /api/employees/{id}` return `EmployeeSummaryResponse` for regular users, `EmployeeResponse` for managers/admins
- [x] Add DELETE endpoints for Locations (`DELETE /api/locations/{id}`) and JobCodes (`DELETE /api/locations/{id}/job-codes/{jc_id}`) — admin only, soft delete via `is_active = False`
- [x] Add frontend DELETE UI for Locations and JobCodes (deactivate buttons on admin Locations page)
- [x] Fix pay period `generate` endpoint: accept `period_group` parameter (was hardcoded to "A"); add group selector to frontend generate form
- [x] Remove redundant `Content-Type` headers from `fetchApi` calls (`fetchApi` sets it by default)
- [x] Fix dev proxy: change `frontend/vite.config.ts` target from port 8002 to 8000 (matching `make dev`)
- [x] Add `frontend/.env.example` with local dev defaults
- [x] Fix `test_auth.py` change-password tests: update from `params=` (query params) to `json=` (body) to match the refactored endpoint
- [x] Sort timesheet list by pay period (newest first), then by employee name (last, first)
- [x] Add location and site code columns to Billing report
- [x] Admin password reset: admin-only endpoint `POST /api/auth/admin-reset-password` and modal UI on Employees page to set a new password for any employee
- [x] Implement site request workflow: employee submission (inline from Time Entry + standalone form), manager approve/reject, auto-creation of Location and JobCode on approval, email notifications
- [x] Implement FastAPI backend with JWT auth and role-based route guards
- [x] Implement React TypeScript frontend with protected routing and manager/admin route scopes
- [x] Implement timesheet and PTO CRUD flows
- [x] Implement submit, approve, reject, and reopen timesheet workflow
- [x] Implement payroll, billing, and Engage export reporting endpoints
- [x] Add PWA support and runtime caching setup in frontend build
- [x] Add database seeding for reference data and initial admin account
- [x] Add root `.env.example` and backend `.env.example` for local/dev bootstrap
