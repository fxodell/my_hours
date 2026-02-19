# Project Context

## Overview

MyHours is a full-stack employee timesheet system that replaces a spreadsheet workflow with role-based web access and API-driven reporting.

Current implementation includes:
- Employee time and PTO entry by pay period
- Submit -> approve/reject workflow with reopen support
- Manager/admin role controls
- Payroll, billing, and Engage CSV exports
- Staggered bi-weekly pay period groups (A/B)
- Password change and reset token flows

## Current Architecture

### Backend
- **Framework:** FastAPI
- **Database:** PostgreSQL with SQLAlchemy 2.x + Alembic
- **Authentication:** JWT bearer tokens + bcrypt password hashes
- **Primary API Base:** `/api/*`
- **Interactive docs:** `/api/docs` and `/api/redoc`

### Frontend
- **Framework:** React 18 + TypeScript (Vite)
- **State/Data:** TanStack Query + React Hook Form
- **Styling:** Tailwind CSS
- **PWA:** `vite-plugin-pwa` with API/network runtime caching

### Deployment/Runtime Options
- Local development via `make` targets
- Local Docker Compose (`db`, `backend`, `frontend`)
- Production details are environment-specific and not yet fully documented here

## Key Directories

- `backend/app/main.py` - FastAPI app and router registration
- `backend/app/api/` - Route handlers (`auth`, `timesheets`, `reports`, etc.)
- `backend/app/models/` - SQLAlchemy models
- `backend/app/schemas/` - Pydantic request/response schemas
- `backend/app/services/` - Cross-cutting services (e.g., email logging service)
- `backend/scripts/seed_data.py` - Seed core reference data + admin user
- `backend/scripts/import_locations.py` - Import location/job code data from spreadsheet
- `frontend/src/pages/` - Main application pages (dashboard, entry, approvals, reports, admin)
- `frontend/src/services/api.ts` - Frontend API client wrapper

## Core Domain Workflow

Timesheet lifecycle:
1. Employee creates/edits a timesheet in `draft` (or updates after `rejected`)
2. Employee submits timesheet (`submitted`)
3. Manager/admin approves (`approved`) or rejects (`rejected`) with reason
4. Manager/admin can reopen submitted/approved timesheets back to `draft`

Access model:
- **Employee:** own timesheets and entries
- **Manager:** approvals + reports + broader timesheet visibility
- **Admin:** manager permissions + employee administration

Pay period model:
- Employees are assigned to Group A or B
- Pay periods are generated per group on alternating 2-week cycles

## Development Setup (Current)

1. Install prerequisites: Python 3.12+, Node.js 20+, Docker (optional but recommended)
2. Start Postgres (`make db-start`) or run full stack via Compose
3. Backend dependencies: `make install`
4. Frontend dependencies: `make install-frontend`
5. Run DB migrations: `make migrate`
6. Seed base data: `make seed`
7. Run backend: `make dev`
8. Run frontend: `make dev-frontend`

## Known Documentation Notes

- This project is actively evolving; docs should prefer "current implementation" language over "planned" where code already exists.
- Email notifications are currently logged by the backend service in development mode rather than sent through SMTP/third-party mail providers.
