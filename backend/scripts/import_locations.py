"""
Import locations and job codes from the Excel timesheet file.
Run after seeding the database with clients.

Usage: python scripts/import_locations.py
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import openpyxl
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models import Client, Location, JobCode

EXCEL_FILE = Path(__file__).parent.parent.parent / "data" / "NFM Timesheet 2-15_2-21.xlsx"

# Map Excel client names to database client names (handle variations)
CLIENT_NAME_MAP = {
    "Apache": "Apache",
    "ADMIN": "NFM",  # Internal admin -> NFM
    "ESS Tech Inc": "ESS Tech Inc",
    "Guidepost": "Guidepost",
    "Hut 8": "Hut 8",
    "JaCo": "JaCo",
    "Jaco": "JaCo",  # Normalize case
    "MP2": "MP2/Shell",
    "Matador": "Matador",
    "Matadot": "Matador",  # Typo fix
    "RPower": "Rpower",
    "Simply Aquatics": "Simply Aquatics",
}


def main():
    print(f"Loading Excel file: {EXCEL_FILE}")

    if not EXCEL_FILE.exists():
        print(f"Error: Excel file not found at {EXCEL_FILE}")
        sys.exit(1)

    wb = openpyxl.load_workbook(EXCEL_FILE, read_only=True)
    ws = wb["Locations"]

    engine = create_engine(settings.database_url_sync)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # Load existing clients into a map
        result = session.execute(select(Client))
        clients = {c.name: c for c in result.scalars().all()}
        print(f"Found {len(clients)} existing clients in database")

        # Track what we create
        locations_created = 0
        job_codes_created = 0
        locations_by_key = {}  # (client_id, region, site_name) -> Location

        # Read all rows from Excel
        rows_processed = 0
        for row in ws.iter_rows(min_row=1, values_only=True):
            rows_processed += 1

            # Safely access row values (some rows may be shorter)
            def get_cell(idx):
                return row[idx] if len(row) > idx else None

            region = get_cell(0)  # Column A
            excel_client = get_cell(1)  # Column B
            site_name = get_cell(3)  # Column D
            job_code = get_cell(4)  # Column E

            # Skip rows without required data
            if not all([region, excel_client, site_name]):
                continue

            # Normalize client name
            client_name = CLIENT_NAME_MAP.get(excel_client, excel_client)
            client = clients.get(client_name)

            if not client:
                print(f"  Warning: Client '{excel_client}' (mapped to '{client_name}') not found, skipping")
                continue

            # Check if location already exists
            location_key = (client.id, region, site_name)
            location = locations_by_key.get(location_key)

            if not location:
                # Check database
                existing = session.execute(
                    select(Location)
                    .where(Location.client_id == client.id)
                    .where(Location.region == region)
                    .where(Location.site_name == site_name)
                ).scalar_one_or_none()

                if existing:
                    location = existing
                    locations_by_key[location_key] = location
                else:
                    # Create new location
                    location = Location(
                        client_id=client.id,
                        region=region,
                        site_name=site_name,
                        is_active=True,
                    )
                    session.add(location)
                    session.flush()  # Get the ID
                    locations_by_key[location_key] = location
                    locations_created += 1

            # Create job code if provided
            if job_code:
                # Convert numeric job codes to strings
                if isinstance(job_code, float):
                    job_code = str(int(job_code))
                else:
                    job_code = str(job_code)

                # Check if job code already exists for this location
                existing_jc = session.execute(
                    select(JobCode)
                    .where(JobCode.location_id == location.id)
                    .where(JobCode.code == job_code)
                ).scalar_one_or_none()

                if not existing_jc:
                    jc = JobCode(
                        location_id=location.id,
                        code=job_code,
                        description=site_name,
                        is_active=True,
                    )
                    session.add(jc)
                    job_codes_created += 1

        session.commit()

        print(f"\nImport complete!")
        print(f"  Rows processed: {rows_processed}")
        print(f"  Locations created: {locations_created}")
        print(f"  Job codes created: {job_codes_created}")

        # Print summary by client
        print(f"\n=== LOCATIONS BY CLIENT ===")
        result = session.execute(
            select(Client.name, Location)
            .join(Location, Location.client_id == Client.id)
            .order_by(Client.name)
        )

        client_counts = {}
        for row in result:
            client_name = row[0]
            client_counts[client_name] = client_counts.get(client_name, 0) + 1

        for client_name, count in sorted(client_counts.items()):
            print(f"  {client_name}: {count} locations")

    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        raise
    finally:
        session.close()
        wb.close()


if __name__ == "__main__":
    main()
