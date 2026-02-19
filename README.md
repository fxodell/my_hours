# MyHours

Employee timesheet management system with a FastAPI backend and React PWA frontend.

## What Is Implemented

- Mobile-friendly time and PTO entry
- Timesheet lifecycle: `draft` -> `submitted` -> `approved`/`rejected`
- Manager approvals, rejections, and reopen actions
- Role-based access (`employee`, `manager`, `admin`)
- Payroll, billing, and Engage export reports
- Password change and reset-token flows
- Staggered bi-weekly pay periods (Group A / Group B)

## Tech Stack

### Backend
- FastAPI
- PostgreSQL
- SQLAlchemy + Alembic
- JWT auth with bcrypt password hashing

### Frontend
- React 18 + TypeScript
- Vite
- TanStack Query
- Tailwind CSS
- PWA via `vite-plugin-pwa`

## Repository Layout

```text
myhours/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   ├── migrations/
│   ├── scripts/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── contexts/
│   │   ├── pages/
│   │   ├── services/
│   │   └── types/
│   ├── package.json
│   └── vite.config.ts
├── docs/
├── docker-compose.yml
└── Makefile
```

## Quick Start (Local Development)

### Prerequisites
- Python 3.12+
- Node.js 20+
- Docker (recommended for local Postgres)

### 1) Install Dependencies

```bash
make install
make install-frontend
```

### 2) Start Database

```bash
make db-start
```

### 3) Run Migrations and Seed Data

```bash
make migrate
make seed
```

### 4) Start Applications

```bash
make dev
make dev-frontend
```

### 5) Open in Browser

- Frontend: `http://localhost:3000`
- API docs: `http://localhost:8000/api/docs`

## Default Seed Admin

After `make seed`, an admin account is created:

- Email: `admin@myhours.local`
- Password: `admin123`

Change this immediately outside local development.

## API Notes

- API base path: `/api`
- Health endpoint: `/api/health`
- Swagger docs: `/api/docs`
- ReDoc: `/api/redoc`

### Common Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/auth/login` | POST | Authenticate user |
| `/api/auth/me` | GET | Get current user |
| `/api/timesheets/current` | GET | Get/create current timesheet |
| `/api/timesheets/{id}/submit` | POST | Submit timesheet |
| `/api/timesheets/{id}/approve` | POST | Approve timesheet |
| `/api/timesheets/{id}/reject` | POST | Reject with reason |
| `/api/reports/payroll` | GET | Payroll report/export |
| `/api/reports/billing` | GET | Billing report/export |
| `/api/reports/engage-export` | GET | Engage CSV export |

## Testing

```bash
make test
```

Or directly:

```bash
cd backend
pytest
```

## Docker Compose

Bring up all services:

```bash
make docker-up
```

Stop services:

```bash
make docker-down
```

## Environment Variables (Backend)

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Async SQLAlchemy database URL |
| `DATABASE_URL_SYNC` | Sync SQLAlchemy URL (migrations/scripts) |
| `SECRET_KEY` | JWT signing key |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime |
| `CORS_ORIGINS` | Allowed frontend origins |

## License

Proprietary - all rights reserved.
