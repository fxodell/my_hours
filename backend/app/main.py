from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api import auth, clients, locations, service_types, employees, timesheets, pay_periods, reports

app = FastAPI(
    title=settings.app_name,
    description="Employee timesheet management system",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r".*" if settings.debug else None,
    allow_origins=settings.cors_origins if not settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(clients.router, prefix="/api")
app.include_router(locations.router, prefix="/api")
app.include_router(service_types.router, prefix="/api")
app.include_router(employees.router, prefix="/api")
app.include_router(timesheets.router, prefix="/api")
app.include_router(pay_periods.router, prefix="/api")
app.include_router(reports.router, prefix="/api")


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/")
async def root():
    return {
        "app": settings.app_name,
        "version": "0.1.0",
        "docs": "/api/docs",
    }
