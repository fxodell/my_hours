"""
Seed the database with initial data from the Excel file analysis.
Run this after creating the database and running migrations.

Usage: python scripts/seed_data.py
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import get_password_hash
from app.models import (
    Base,
    Company,
    Client,
    ServiceType,
    Employee,
    PayPeriod,
)

engine = create_engine(settings.database_url_sync)
SessionLocal = sessionmaker(bind=engine)


def seed_company(session):
    """Create or retrieve the default company."""
    existing = session.query(Company).filter_by(slug="default-company").first()
    if not existing:
        company = Company(
            name="Default Company",
            slug="default-company",
            is_active=True,
        )
        session.add(company)
        session.commit()
        print(f"  Created default company: {company.name}")
        return company
    else:
        print(f"  Default company already exists: {existing.name}")
        return existing


def seed_clients(session, company):
    """Seed clients from the Excel analysis."""
    clients = [
        {"name": "Apache", "industry": "O&G"},
        {"name": "City of Midlothian", "industry": "Fiber"},
        {"name": "Downunder Geo Solutions", "industry": "Power"},
        {"name": "ESS Tech Inc", "industry": "Water"},
        {"name": "Flexile", "industry": "Data"},
        {"name": "Guidepost", "industry": "Admin"},
        {"name": "Hut 8", "industry": "Data"},
        {"name": "JaCo", "industry": "O&G"},
        {"name": "Matador", "industry": "O&G"},
        {"name": "MP2/Shell", "industry": "O&G"},
        {"name": "NFM", "industry": "Admin"},
        {"name": "Rpower", "industry": "Power"},
        {"name": "Simply Aquatics", "industry": "Water"},
        {"name": "Tesnett", "industry": "O&G"},
        {"name": "Other", "industry": None},
    ]

    for client_data in clients:
        existing = session.query(Client).filter_by(
            company_id=company.id, name=client_data["name"]
        ).first()
        if not existing:
            session.add(Client(company_id=company.id, **client_data))
            print(f"  Created client: {client_data['name']}")

    session.commit()


def seed_service_types(session, company):
    """Seed service types from the Excel analysis."""
    service_types = [
        {"name": "Automation", "is_billable": True},
        {"name": "Emissions/Flare", "is_billable": True},
        {"name": "Operations", "is_billable": True},
        {"name": "Installations", "is_billable": True},
        {"name": "Build Manifold - In House Purchase", "is_billable": True},
        {"name": "Build Manifold - 3rd Party Vendor", "is_billable": True},
        {"name": "SP", "is_billable": True},
        {"name": "PT", "is_billable": True},
        {"name": "FV", "is_billable": True},
        {"name": "OT", "is_billable": True},
        {"name": "CRQ", "is_billable": True},
        {"name": "Communications", "is_billable": True},
        {"name": "Conference Call Meeting", "is_billable": False},
        {"name": "Consulting", "is_billable": True},
        {"name": "Critical Analysis", "is_billable": True},
        {"name": "Installation", "is_billable": True},
        {"name": "Mapping", "is_billable": True},
        {"name": "Programing", "is_billable": True},
        {"name": "Repair", "is_billable": True},
        {"name": "SCADA Services", "is_billable": True},
        {"name": "Site Inspection", "is_billable": True},
        {"name": "Testing", "is_billable": True},
        {"name": "Travel", "is_billable": False},
        {"name": "Troubleshooting", "is_billable": True},
        {"name": "NFM Truck Maintenance", "is_billable": False},
        {"name": "Admin", "is_billable": False},
        {"name": "Person Truck Reimbursment", "is_billable": False},
    ]

    for st_data in service_types:
        existing = session.query(ServiceType).filter_by(
            company_id=company.id, name=st_data["name"]
        ).first()
        if not existing:
            session.add(ServiceType(company_id=company.id, **st_data))
            print(f"  Created service type: {st_data['name']}")

    session.commit()


def seed_admin_user(session, company):
    """Create an admin user for initial access."""
    admin_email = "admin@myhours.local"
    existing = session.query(Employee).filter_by(email=admin_email).first()

    if not existing:
        admin = Employee(
            company_id=company.id,
            email=admin_email,
            password_hash=get_password_hash("admin123"),  # Change in production!
            first_name="Admin",
            last_name="User",
            hire_date=date.today(),
            pay_period_group="A",
            is_manager=True,
            is_admin=True,
            is_active=True,
        )
        session.add(admin)
        session.commit()
        print(f"  Created admin user: {admin_email} (password: admin123)")
    else:
        print(f"  Admin user already exists: {admin_email}")


def seed_pay_periods(session, company):
    """Generate initial weekly Mon-Sun pay periods."""
    today = date.today()
    # Find most recent Monday (weekday(): 0=Mon, 6=Sun)
    days_since_monday = today.weekday()
    start_date = today - timedelta(days=days_since_monday)

    for i in range(8):  # 8 weekly periods
        period_start = start_date + timedelta(days=7 * i)
        period_end = period_start + timedelta(days=6)

        existing = (
            session.query(PayPeriod)
            .filter_by(start_date=period_start)
            .first()
        )

        if not existing:
            pay_period = PayPeriod(
                company_id=company.id,
                period_group="A",
                start_date=period_start,
                end_date=period_end,
                status="open",
            )
            session.add(pay_period)
            print(f"  Created pay period: {period_start} to {period_end}")

    session.commit()


def main():
    print("Seeding database...")

    session = SessionLocal()

    try:
        print("\nSeeding default company...")
        company = seed_company(session)

        print("\nSeeding clients...")
        seed_clients(session, company)

        print("\nSeeding service types...")
        seed_service_types(session, company)

        print("\nSeeding admin user...")
        seed_admin_user(session, company)

        print("\nSeeding pay periods...")
        seed_pay_periods(session, company)

        print("\nSeed complete!")

    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
