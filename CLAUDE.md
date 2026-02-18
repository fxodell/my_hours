# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MyHours is a mobile-first employee timesheet management system replacing an Excel-based workflow. Built with:
- **Backend:** FastAPI (Python 3.12) with SQLAlchemy ORM
- **Database:** PostgreSQL
- **Frontend:** React PWA with Tailwind CSS

## Development Commands

```bash
# Backend setup
make install           # Install Python dependencies
make db-start          # Start PostgreSQL (Docker)
make migrate           # Run database migrations
make seed              # Seed initial data

# Frontend setup
make install-frontend  # Install npm dependencies

# Development
make dev               # Backend at http://localhost:8000
make dev-frontend      # Frontend at http://localhost:3000
make dev-all           # Run both concurrently

# API docs: http://localhost:8000/api/docs
```

## Project Structure

```
backend/
├── app/
│   ├── api/           # FastAPI route handlers
│   │   ├── auth.py          # Login, current user, password change
│   │   ├── clients.py       # Client CRUD
│   │   ├── employees.py     # Employee CRUD
│   │   ├── pay_periods.py   # Pay period management
│   │   ├── reports.py       # Payroll/billing reports with CSV/Excel export
│   │   ├── service_types.py # Service type CRUD
│   │   └── timesheets.py    # Timesheets, time entries, PTO, approvals
│   ├── core/          # Config, database, security
│   ├── models/        # SQLAlchemy ORM models
│   ├── schemas/       # Pydantic validation schemas
│   └── main.py        # FastAPI app entry point
├── migrations/        # Alembic database migrations
└── scripts/seed_data.py

frontend/
├── src/
│   ├── components/    # Shared components (Layout)
│   ├── contexts/      # React contexts (AuthContext)
│   ├── pages/         # Route pages
│   │   ├── Login.tsx
│   │   ├── Dashboard.tsx
│   │   ├── TimeEntry.tsx
│   │   ├── Timesheets.tsx
│   │   ├── TimesheetDetail.tsx
│   │   ├── Approvals.tsx      # Manager approval workflow
│   │   └── Profile.tsx
│   ├── services/api.ts        # API client
│   ├── types/index.ts         # TypeScript types
│   └── styles/index.css       # Tailwind styles
└── public/
```

## Data Model

### Core Entities
- **Employee** - Users with `pay_period_group` (A or B) for staggered bi-weekly pay
- **PayPeriod** - Bi-weekly periods, grouped by A/B for staggered schedules
- **Timesheet** - One per employee per pay period (draft → submitted → approved/rejected)
- **TimeEntry** - Hours worked with client, location, job code, service type
- **PTOEntry** - PTO hours (personal, sick, holiday)
- **Client** - Billable clients with industry classification
- **ServiceType** - Types of work (SCADA Services, Automation, etc.)

### Timesheet Workflow
1. Employee creates/edits time entries (status: `draft`)
2. Employee submits timesheet (status: `submitted`)
3. Manager approves (status: `approved`) or rejects with reason (status: `rejected`)
4. If rejected, employee can edit and resubmit

### Pay Period Staggering
- Group A and Group B employees are on alternating 2-week cycles
- This allows payroll processing to be spread across weeks

## API Endpoints

### Authentication
- `POST /api/auth/login` - Get JWT token
- `GET /api/auth/me` - Current user info

### Timesheets
- `GET /api/timesheets/current` - Get/create current timesheet
- `GET /api/timesheets/{id}` - Get timesheet details
- `POST /api/timesheets/{id}/submit` - Submit for approval
- `POST /api/timesheets/{id}/approve` - Manager approval
- `POST /api/timesheets/{id}/reject` - Manager rejection

### Time Entries
- `GET /api/timesheets/{id}/entries` - List entries
- `POST /api/timesheets/{id}/entries` - Add entry
- `PATCH /api/timesheets/{id}/entries/{entry_id}` - Update entry
- `DELETE /api/timesheets/{id}/entries/{entry_id}` - Delete entry

### Reports (Manager only)
- `GET /api/reports/payroll?format=excel` - Payroll export
- `GET /api/reports/billing?format=excel` - Billing by client
- `GET /api/reports/hours-by-employee?format=csv` - Hours summary
- `GET /api/reports/hours-by-job-code?format=csv` - Hours by job code

## Required Reading

Before making changes, read:
- `docs/CONTEXT.md` - Project overview and architecture
- `docs/TASKS.md` - Current sprint and backlog items

## Development Guidelines

- Keep changes minimal and scoped
- Prefer small diffs and incremental commits
- After modifying logic, add tests or provide exact manual test steps
- Do not change architecture without adding an ADR to `docs/DECISIONS.md`
- If behavior changes, update `docs/CONTEXT.md`

## File Organization

- Never edit generated, build, or vendor files
- Do not create throwaway files in the repo root
- Put experiments in `/scratch` (gitignored) or `/sandbox`
- Before finishing a task, remove trial files or move them to `/scratch`

## Authentication

- JWT-based via `/api/auth/login`
- Token in Authorization header: `Bearer <token>`
- Default admin: `admin@myhours.local` / `admin123` (change in production!)

## Deployment

- **Dev:** Local MacBook with Docker for PostgreSQL
- **Prod:** Google Compute Engine VM
  - Copy `backend/.env.example` to `.env` and configure
  - Run migrations: `alembic upgrade head`
  - Seed data: `python scripts/seed_data.py`
  - Run with: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
