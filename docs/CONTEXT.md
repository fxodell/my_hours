# Project Context

## Overview

MyHours is a custom employee timesheet management system replacing an Excel-based workflow. The system supports:
- Mobile-first time entry for field technicians
- Manager approval workflows
- Payroll exports for Engage (manual/CSV)
- Future QuickBooks integration for invoicing
- Staggered bi-weekly pay periods (Group A and Group B)

## Architecture

### Backend (FastAPI)
- **Framework:** FastAPI with async SQLAlchemy
- **Database:** PostgreSQL
- **Auth:** JWT tokens with bcrypt password hashing
- **API:** RESTful endpoints at `/api/*`

### Frontend (Planned)
- **Framework:** React with Tailwind CSS
- **Type:** Progressive Web App (PWA)
- **Mobile:** Installable, offline-capable

### Deployment (Planned)
- **Dev:** Local MacBook with Docker for PostgreSQL
- **Prod:** Google Compute Engine VM

## Key Files

- `backend/app/main.py` - FastAPI application entry point
- `backend/app/models/` - SQLAlchemy ORM models
- `backend/app/api/` - API route handlers
- `backend/app/core/config.py` - Environment configuration
- `backend/scripts/seed_data.py` - Database seeding script

## Development Setup

1. Install Python 3.12+
2. Start PostgreSQL: `make db-start`
3. Install deps: `make install`
4. Copy `.env.example` to `.env` in backend/
5. Run migrations: `make migrate`
6. Seed data: `make seed`
7. Start server: `make dev`

## Data Model

Timesheets follow this workflow:
1. Employee creates/edits timesheet entries (draft)
2. Employee submits timesheet
3. Manager approves or rejects with reason
4. If rejected, employee can edit and resubmit

Pay periods are staggered:
- Group A and Group B employees are on alternating 2-week cycles
- This allows payroll processing to be spread across weeks
