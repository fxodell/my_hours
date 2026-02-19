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

Vite dev server proxies `/api/*` requests to `http://localhost:8002` (see `frontend/vite.config.ts`). The `fetchApi` helper in `frontend/src/services/api.ts` handles JWT token from localStorage, auto-redirects to `/login` on 401.

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
`draft` -> `submitted` -> `approved` or `rejected` (rejected returns to editable, can resubmit)

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

## Authentication

- JWT-based via `POST /api/auth/login` (OAuth2 password form)
- Token in `Authorization: Bearer <token>` header
- Default admin: `admin@myhours.local` / `admin123`

## Deployment

- **Dev:** Docker for PostgreSQL, local Python/Node for app
- **Prod:** Google Compute Engine VM, or full Docker Compose (`docker-compose up -d`)
- Backend `.env` from `.env.example`; migrations via `alembic upgrade head`
