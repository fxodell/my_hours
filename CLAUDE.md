# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MyHours is a mobile-first employee timesheet management system. Backend is FastAPI (Python 3.12) with async SQLAlchemy on PostgreSQL. Frontend is a React PWA (TypeScript, Vite, Tailwind CSS, TanStack Query).

## Development Commands

```bash
# Setup
make install           # Install backend Python deps
make install-frontend  # Install frontend npm deps
make db-start          # Start PostgreSQL via Docker
make migrate           # Run Alembic migrations
make seed              # Seed database with initial data
make import-locations  # Import locations/job codes from Excel (requires data/ dir)

# Development
make dev               # Backend at http://localhost:8000
make dev-frontend      # Frontend at http://localhost:3000 (proxies /api to backend)
make dev-all           # Run both concurrently

# Testing
make test                               # Run all backend tests
cd backend && pytest tests/test_auth.py # Run a single test file
cd backend && pytest -k "test_login"    # Run tests matching a name

# Database migrations
make migrate                                          # Apply migrations
cd backend && alembic revision --autogenerate -m "description"  # Create new migration

# Frontend
cd frontend && npm run lint    # ESLint
cd frontend && npm run build   # Production build (runs tsc first)

# API docs: http://localhost:8000/api/docs
```

## Architecture

### Backend: Dual Database Engines

The app uses two SQLAlchemy engines (`backend/app/core/database.py`):
- **Async engine** (`asyncpg`): Used by FastAPI route handlers via `get_db()` dependency injection
- **Sync engine** (`psycopg2`): Used by Alembic migrations and seed scripts

Both are configured via `DATABASE_URL` and `DATABASE_URL_SYNC` in `.env`.

### Backend: Model Patterns

All models inherit from `Base` (declarative base) and use two mixins from `backend/app/models/base.py`:
- **UUIDMixin**: Provides `id` column as PostgreSQL UUID primary key (auto-generated `uuid4`)
- **TimestampMixin**: Provides `created_at` and `updated_at` with server-side defaults

### Backend: API Structure

All routers are mounted under `/api` prefix in `main.py`. Auth uses JWT tokens (python-jose) with bcrypt password hashing. The `get_current_user` dependency extracts the employee from the JWT `sub` claim (which contains the employee UUID).

### Frontend: API Proxy

Vite dev server proxies `/api/*` requests to `http://localhost:8000` (see `frontend/vite.config.ts`), matching the backend port from `make dev`. The `fetchApi` helper in `frontend/src/services/api.ts` handles JWT token from localStorage, auto-redirects to `/login` on 401.

### Frontend: State Management

Uses TanStack Query for server state. Auth state is in React Context (`frontend/src/contexts/AuthContext.tsx`). Forms use react-hook-form.

### Frontend: Timesheet Editability Pattern

Shared helpers in `frontend/src/timesheetStatus.ts` control form behavior across all entry pages:
- `isTimesheetEditable(status)` — returns `true` for `draft` or `rejected`
- `isTimesheetReadOnly(status)` — returns `true` for `submitted` or `approved`
- `getEntryDateMax(endDate)` — returns `min(today, endDate)` to prevent future-dated entries

All entry form pages (`TimeEntry.tsx`, `TimeEntryEdit.tsx`, `PTOEntry.tsx`, `PTOEntryEdit.tsx`) use `disabled={!canEdit}` on inputs and show a yellow read-only banner when the timesheet is not editable.

### Frontend: Entry Form Timesheet Targeting

`TimeEntry.tsx` and `PTOEntry.tsx` accept an optional `?timesheet=<id>` query parameter. When present, entries are created against that specific timesheet; otherwise they default to `getCurrentTimesheet()`. `TimesheetDetail.tsx` passes this param in its "Add Time" and "Add PTO" links so entries target the correct timesheet.

### Frontend: Cascading Select Pattern

Entry forms use a Client → Location → Job Code cascade:
1. User selects Client → triggers Location query (`enabled: !!selectedClientId`)
2. User selects Location → triggers Job Code query (`enabled: !!selectedLocationId`)
3. Changing a parent resets dependent fields via `useEffect` + `setValue`

### Test Infrastructure

Tests use **in-memory SQLite** (aiosqlite) instead of PostgreSQL. Key fixtures in `backend/tests/conftest.py`:
- `client` - AsyncClient with ASGI transport, DB dependency override
- `test_user` / `test_manager` - Pre-created employees
- `auth_headers` / `manager_auth_headers` - JWT auth headers for test users

All fixtures are function-scoped: each test gets a fresh in-memory SQLite database, so tests can run together without isolation issues.

## Data Model

### Core Entities
- **Employee** - Users with `pay_period_group` (A or B), roles (`is_manager`, `is_admin`)
- **PayPeriod** - Bi-weekly periods, grouped by A/B for staggered schedules
- **Timesheet** - One per employee per pay period (draft -> submitted -> approved/rejected)
- **TimeEntry** - Hours worked: client, location, job code, service type, work mode
- **PTOEntry** - PTO hours (personal, sick, holiday, other)
- **Client** - Billable clients with industry classification
- **Location** - Physical locations belonging to a client
- **JobCode** - Job codes belonging to a location
- **ServiceType** - Types of work (SCADA Services, Automation, etc.)

### Relationships
Client -> Location -> JobCode (hierarchical). TimeEntry references client, location, job_code, and service_type.

### Timesheet Workflow
`draft` -> `submitted` -> `approved` or `rejected` (rejected returns to editable, can resubmit). Managers can reopen approved/submitted timesheets back to draft.

Backend enforces editability: time entry and PTO entry create/update/delete endpoints reject mutations when timesheet status is not `draft` or `rejected`. Both time entry and PTO entry dates are validated against pay period bounds.

### Pay Period Staggering
Group A and Group B employees are on alternating 2-week cycles, spreading payroll processing across weeks. Pay period endpoints and timesheet creation enforce group matching — employees can only see and create timesheets in their assigned group's periods.

## Required Reading

Before making changes, read:
- `docs/CONTEXT.md` - Project overview and architecture
- `docs/TASKS.md` - Current sprint and backlog items

## Development Guidelines

- Keep changes minimal and scoped; prefer small diffs and incremental commits
- After modifying logic, add tests or provide exact manual test steps
- Do not change architecture without adding an ADR to `docs/DECISIONS.md`
- If behavior changes, update `docs/CONTEXT.md`
- Never edit generated, build, or vendor files
- Do not create throwaway files in the repo root; use `/scratch` (gitignored) or `/sandbox`
- Before finishing a task, remove trial files or move them to `/scratch`

## Role-Based Access

Three tiers enforced via dependency injection in `backend/app/api/deps.py`:
- **`CurrentUser`** — Any authenticated active employee
- **`CurrentManager`** — `is_manager=True` OR `is_admin=True`
- **`CurrentAdmin`** — `is_admin=True` only

| Capability | Employee | Manager | Admin |
|---|---|---|---|
| Own timesheets & entries | Yes | Yes | Yes |
| View employee list (summary only, no rates) | Yes | - | - |
| View employee list (full, with hourly_rate) | - | Yes | Yes |
| View all timesheets | - | Yes | Yes |
| Approve/reject/reopen/delete timesheets | - | Yes | Yes |
| Reports & exports | - | Yes | Yes |
| Manage employees, clients, service types, locations, pay periods | - | - | Yes |

Frontend enforces via `ProtectedRoute`, `ManagerRoute`, `AdminRoute` wrappers in `App.tsx`.

## Authentication

- JWT-based via `POST /api/auth/login` (OAuth2 password form)
- Token in `Authorization: Bearer <token>` header
- Default admin: `admin@myhours.local` / `admin123`
- Password change: `POST /api/auth/change-password`
- Password reset: `POST /api/auth/request-reset` + `POST /api/auth/reset-password`

## API Endpoints (Key)

### Timesheets
- `GET /api/timesheets` - List timesheets (ordered by pay period start_date desc, then employee last_name, first_name)
- `GET /api/timesheets/current` - Get/create current timesheet for logged-in user
- `GET /api/timesheets/{id}` - Get timesheet details
- `POST /api/timesheets/{id}/submit` - Submit for approval
- `POST /api/timesheets/{id}/approve` - Manager approval
- `POST /api/timesheets/{id}/reject` - Manager rejection
- `POST /api/timesheets/{id}/reopen` - Reopen approved/submitted timesheet to draft (manager only)
- `DELETE /api/timesheets/{id}` - Delete timesheet (manager/admin only)

### Reports (Manager only)
- `GET /api/reports/payroll?format=csv` - Payroll export (one row per weekly timesheet)
- `GET /api/reports/payroll-biweekly?period_group=A&anchor_start_date=2026-03-15&format=csv` - Biweekly payroll rollup (one row per employee for two consecutive weeks; per-day hours + aggregate totals; JSON/CSV/Excel)
- `GET /api/reports/employee-detail?employee_id=<uuid>&start_date=2026-03-01&end_date=2026-03-31&format=csv` - Line-level detail for one or many employees (manager only; use `employee_ids=uuid1,uuid2` for multiple; filters: `timesheet_status`, `pay_period_status`, `include_pto`)
- `GET /api/reports/my-time-detail?start_date=2026-03-01&end_date=2026-03-31&format=csv` - Self-service export of own entries (any authenticated user; same filters as employee-detail minus employee selection)
- `GET /api/reports/billing?format=csv` - Billing by client
- `GET /api/reports/hours-by-employee?format=csv` - Hours summary
- `GET /api/reports/hours-by-job-code?format=csv` - Hours by job code
- `GET /api/reports/engage-export?pay_period_id=<uuid>` - Engage payroll system export

### Admin CRUD (Admin only)
Standard REST pattern for each resource — `GET` (list), `GET /{id}`, `POST`, `PATCH /{id}`, `DELETE /{id}`:
- `/api/employees` — Employee management
- `/api/clients` — Client management
- `/api/service-types` — Service type management
- `/api/locations` — Location management (nested: `/api/locations/{id}/job-codes`; DELETE soft-deactivates)
- `/api/pay-periods` — Pay period management (extra: `POST /generate`, `POST /{id}/close`)

## Frontend: Reusable Components

- **SearchableSelect** (`frontend/src/components/SearchableSelect.tsx`) - Dropdown with search/filter, keyboard navigation (arrows + Enter), Escape to clear/close. Used for large option lists like locations.

## Deployment

### Local Development
- Docker for PostgreSQL, local Python/Node for app
- Full Docker Compose: `docker-compose up -d`

### Production (GCE VM at myhours.nfmconsulting.com)
- **Host nginx** serves static frontend from `/var/www/html` and proxies `/api/` to backend container on port 8000
- SSL via Let's Encrypt (certbot)
- Backend runs in Docker; code may be volume-mounted (`app/`, `migrations/`, `scripts/`) or baked into the image
- **To see backend code changes in production:** On the server run `git pull` then `./scripts/production-restart-backend.sh` (or `docker compose restart backend`). No image rebuild needed if app code is mounted; if you deploy via new image, run `docker compose build backend && docker compose up -d backend`. See `docs/DEPLOY_PRODUCTION.md` for the full checklist.
- Frontend deploy: `cd frontend && npm run build && sudo cp -r dist/* /var/www/html/`
- Backend `.env` from `.env.example`; migrations: `docker compose exec backend alembic upgrade head`
- Import locations: `docker compose exec backend python scripts/import_locations.py` (requires `/data` volume with Excel file)

## Known Issues

- Email notifications are logged in dev mode rather than sent via SMTP
