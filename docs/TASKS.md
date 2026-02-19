# Tasks

## Current Sprint
- [ ] Fix dev proxy mismatch so frontend `/api` target matches backend dev port (`frontend/vite.config.ts` vs `make dev`)
- [ ] Align Docker backend healthcheck path with FastAPI health route (`/api/health`)
- [ ] Add `frontend/.env.example` with required frontend env vars and local defaults
- [ ] Document role-based test scenarios for employee/manager/admin flows
- [ ] Add API integration tests for timesheet submit/approve/reject/reopen lifecycle
- [ ] Add API integration tests for report export endpoints (CSV and Excel)
- [ ] Reconcile backend health test path (`backend/tests/test_health.py` uses `/health` while app exposes `/api/health`)

## Backlog
- [ ] Replace development email logger with configurable SMTP/provider implementation
- [ ] Add QuickBooks export/invoicing integration path
- [ ] Add audit logging for status transitions and sensitive admin actions
- [ ] Add stronger password policy and optional MFA support
- [ ] Add seed/import idempotency tests and data validation checks
- [ ] Improve dashboard analytics and manager review queue UX
- [ ] Add CI pipeline for lint/test/build checks

## Completed
- [x] Implement FastAPI backend with JWT auth and role-based route guards
- [x] Implement React TypeScript frontend with protected routing and manager/admin route scopes
- [x] Implement timesheet and PTO CRUD flows
- [x] Implement submit, approve, reject, and reopen timesheet workflow
- [x] Implement payroll, billing, and Engage export reporting endpoints
- [x] Add PWA support and runtime caching setup in frontend build
- [x] Add database seeding for reference data and initial admin account
- [x] Add root `.env.example` and backend `.env.example` for local/dev bootstrap
