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
    Client,
    ServiceType,
    Employee,
    PayPeriod,
)

engine = create_engine(settings.database_url_sync)
SessionLocal = sessionmaker(bind=engine)


def seed_clients(session):
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
        existing = session.query(Client).filter_by(name=client_data["name"]).first()
        if not existing:
            session.add(Client(**client_data))
            print(f"  Created client: {client_data['name']}")

    session.commit()


def seed_service_types(session):
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
        existing = session.query(ServiceType).filter_by(name=st_data["name"]).first()
        if not existing:
            session.add(ServiceType(**st_data))
            print(f"  Created service type: {st_data['name']}")

    session.commit()


def seed_admin_user(session):
    """Create an admin user for initial access."""
    admin_email = "admin@myhours.local"
    existing = session.query(Employee).filter_by(email=admin_email).first()

    if not existing:
        admin = Employee(
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


def seed_pay_periods(session):
    """Generate initial pay periods for both groups."""
    # Start from the beginning of the current week
    today = date.today()
    # Find last Sunday
    start_date = today - timedelta(days=today.weekday() + 1)

    for group in ["A", "B"]:
        group_start = start_date if group == "A" else start_date + timedelta(days=7)

        for i in range(4):  # 4 pay periods (8 weeks)
            period_start = group_start + timedelta(days=14 * i)
            period_end = period_start + timedelta(days=13)

            existing = (
                session.query(PayPeriod)
                .filter_by(period_group=group, start_date=period_start)
                .first()
            )

            if not existing:
                pay_period = PayPeriod(
                    period_group=group,
                    start_date=period_start,
                    end_date=period_end,
                    status="open",
                )
                session.add(pay_period)
                print(f"  Created pay period: Group {group}, {period_start} to {period_end}")

    session.commit()


def main():
    print("Seeding database...")

    session = SessionLocal()

    try:
        print("\nSeeding clients...")
        seed_clients(session)

        print("\nSeeding service types...")
        seed_service_types(session)

        print("\nSeeding admin user...")
        seed_admin_user(session)

        print("\nSeeding pay periods...")
        seed_pay_periods(session)

        print("\nSeed complete!")

    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
