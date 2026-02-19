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

Vite dev server proxies `/api/*` requests to `http://localhost:8002` (see `frontend/vite.config.ts`). **Note:** `make dev` runs the backend on port 8000, so for local dev either change the proxy target or run uvicorn on 8002. The `fetchApi` helper in `frontend/src/services/api.ts` handles JWT token from localStorage, auto-redirects to `/login` on 401.

### Frontend: State Management

Uses TanStack Query for server state. Auth state is in React Context (`frontend/src/contexts/AuthContext.tsx`). Forms use react-hook-form.

### Test Infrastructure

Tests use **in-memory SQLite** (aiosqlite) instead of PostgreSQL. Key fixtures in `backend/tests/conftest.py`:
- `client` - AsyncClient with ASGI transport, DB dependency override
- `test_user` / `test_manager` - Pre-created employees
- `auth_headers` / `manager_auth_headers` - JWT auth headers for test users

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

### Pay Period Staggering
Group A and Group B employees are on alternating 2-week cycles, spreading payroll processing across weeks.

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
- `GET /api/timesheets/current` - Get/create current timesheet for logged-in user
- `GET /api/timesheets/{id}` - Get timesheet details
- `POST /api/timesheets/{id}/submit` - Submit for approval
- `POST /api/timesheets/{id}/approve` - Manager approval
- `POST /api/timesheets/{id}/reject` - Manager rejection
- `POST /api/timesheets/{id}/reopen` - Reopen approved/submitted timesheet to draft (manager only)
- `DELETE /api/timesheets/{id}` - Delete timesheet (manager/admin only)

### Reports (Manager only)
- `GET /api/reports/payroll?format=excel` - Payroll export
- `GET /api/reports/billing?format=excel` - Billing by client
- `GET /api/reports/hours-by-employee?format=csv` - Hours summary
- `GET /api/reports/hours-by-job-code?format=csv` - Hours by job code

### Admin CRUD (Admin only)
Standard REST pattern for each resource — `GET` (list), `GET /{id}`, `POST`, `PATCH /{id}`, `DELETE /{id}`:
- `/api/employees` — Employee management
- `/api/clients` — Client management
- `/api/service-types` — Service type management
- `/api/locations` — Location management (nested: `/api/locations/{id}/job-codes`)
- `/api/pay-periods` — Pay period management (extra: `POST /generate`, `POST /{id}/close`)

## Frontend: Admin Pages

All under `AdminRoute` guard, accessible from Dashboard "Admin Tools" section:
- `/employees` — `Employees.tsx` — Create, edit, toggle active, assign roles
- `/clients` — `Clients.tsx` — Create, edit, delete clients
- `/service-types` — `ServiceTypes.tsx` — Create, edit, delete service types
- `/locations` — `Locations.tsx` — Client selector → location CRUD → expandable job codes per location
- `/pay-periods` — `PayPeriods.tsx` — List/filter, create single, generate bulk (A/B staggered), close periods

All follow the same pattern: `useQuery` for listing, `useMutation` for CRUD, inline card-based forms, TanStack Query invalidation on success.

## Frontend: Reusable Components

- **SearchableSelect** (`frontend/src/components/SearchableSelect.tsx`) - Dropdown with search/filter, keyboard navigation (arrows + Enter), Escape to clear/close. Used for large option lists like locations.

## Deployment

### Local Development
- Docker for PostgreSQL, local Python/Node for app
- Full Docker Compose: `docker-compose up -d`

### Production (GCE VM at myhours.nfmconsulting.com)
- **Host nginx** serves static frontend from `/var/www/html` and proxies `/api/` to backend container on port 8000
- SSL via Let's Encrypt (certbot)
- Backend runs in Docker with volume mounts for live code reload
- Frontend deploy: `cd frontend && npm run build && sudo cp -r dist/* /var/www/html/`
- Backend `.env` from `.env.example`; migrations: `docker compose exec backend alembic upgrade head`
- Import locations: `docker compose exec backend python scripts/import_locations.py` (requires `/data` volume with Excel file)
