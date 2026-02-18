# MyHours - Employee Timesheet Management System

A modern, mobile-first PWA for managing employee timesheets with staggered bi-weekly pay periods.

## Features

- **Mobile-First PWA**: Installable progressive web app optimized for mobile use
- **Staggered Pay Periods**: Support for Group A and Group B bi-weekly pay periods
- **Time Entry Management**: Track work hours by client, location, job code, and service type
- **PTO Tracking**: Personal, sick, holiday, and other PTO types
- **Approval Workflow**: Submit → Approve/Reject cycle with manager notifications
- **Reports & Export**: Payroll reports, billing reports, and Engage-specific export
- **Offline Support**: PWA caching for offline access

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework with async support
- **PostgreSQL** - Relational database
- **SQLAlchemy 2.0** - Async ORM with Alembic migrations
- **JWT Authentication** - Secure token-based auth

### Frontend
- **React 18** - UI library with hooks
- **TypeScript** - Type safety
- **TanStack Query** - Data fetching and caching
- **Tailwind CSS** - Utility-first styling
- **Vite** - Fast build tool with HMR
- **PWA** - Service worker with offline caching

## Project Structure

```
my_hours/
├── backend/
│   ├── app/
│   │   ├── api/           # API endpoints
│   │   │   ├── auth.py    # Authentication
│   │   │   ├── timesheets.py
│   │   │   ├── employees.py
│   │   │   ├── reports.py
│   │   │   └── ...
│   │   ├── core/          # Configuration, security, database
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   └── services/      # Business logic (email, etc.)
│   ├── migrations/        # Alembic database migrations
│   ├── tests/             # Pytest tests
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/    # Reusable UI components
│   │   ├── contexts/      # React contexts (Auth)
│   │   ├── pages/         # Page components
│   │   ├── services/      # API client
│   │   ├── types/         # TypeScript types
│   │   └── styles/        # CSS
│   ├── Dockerfile
│   └── nginx.conf
└── docker-compose.yml
```

## Getting Started

### Prerequisites
- Python 3.12+
- Node.js 20+
- PostgreSQL 16+

### Development Setup

1. **Clone and setup backend:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   
   # Configure database
   export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/myhours"
   export SECRET_KEY="your-secret-key"
   
   # Run migrations
   alembic upgrade head
   
   # Start server
   uvicorn app.main:app --reload --port 8000
   ```

2. **Setup frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Access the app:**
   - Frontend: http://localhost:3000
   - API docs: http://localhost:8000/docs

### Docker Deployment

```bash
# Copy and configure environment
cp .env.example .env
# Edit .env with your settings

# Build and run
docker-compose up -d

# Run migrations
docker-compose exec backend alembic upgrade head
```

## API Documentation

Interactive API documentation is available at `/docs` (Swagger UI) or `/redoc` (ReDoc).

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/login` | POST | User login |
| `/api/auth/me` | GET | Current user info |
| `/api/timesheets/current` | GET | Get current timesheet |
| `/api/timesheets/{id}/entries` | POST | Add time entry |
| `/api/timesheets/{id}/submit` | POST | Submit for approval |
| `/api/timesheets/{id}/approve` | POST | Approve timesheet |
| `/api/reports/payroll` | GET | Payroll report |
| `/api/reports/engage-export` | GET | Engage-formatted export |

## Data Models

### Employee
- Email, name, hire date
- Pay period group (A or B)
- Role (employee, manager, admin)
- Optional: hourly rate, Engage ID, QuickBooks ID

### Timesheet
- Employee + pay period combination
- Status: draft, submitted, approved, rejected
- Contains time entries and PTO entries

### Time Entry
- Work date, hours, client, location, job code
- Service type, work mode (remote/on-site)
- Optional: description, vehicle reimbursement, bonus eligible

### PTO Entry
- PTO date, type (personal/sick/holiday/other)
- Hours, notes

## Pay Period Schedule

The system supports staggered bi-weekly pay periods:
- **Group A**: Starts on the 1st and 15th
- **Group B**: Starts on the 8th and 22nd

Each employee is assigned to a group based on their hire date.

## Testing

```bash
cd backend
pytest                    # Run all tests
pytest --cov=app         # With coverage
pytest tests/test_auth.py # Specific test file
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `SECRET_KEY` | JWT signing key | Required |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry | 480 (8 hours) |

## License

Proprietary - All rights reserved
