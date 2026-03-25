"""
Import / update locations from data/ApacheSiteListGPS.csv.

Sets site_code from api_number, latitude, longitude, and optional job_codes column
(semicolon- or comma-separated). Matches existing rows by client + site_name
(case-insensitive), or creates a new location using county as region.

Usage (from backend/, with DATABASE_URL_SYNC in env):

  python scripts/import_apache_site_gps.py
  python scripts/import_apache_site_gps.py --dry-run

Requires client named "Apache" (or pass --client-name).
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.models import Client, Location, JobCode  # noqa: E402

CSV_PATH = Path(__file__).parent.parent.parent / "data" / "ApacheSiteListGPS.csv"


def split_job_codes(raw: str | None) -> list[str]:
    if raw is None or not str(raw).strip():
        return []
    parts = re.split(r"[;,]", str(raw))
    return [p.strip() for p in parts if p.strip()]


def to_decimal(val: str | None) -> Decimal | None:
    if val is None or str(val).strip() == "":
        return None
    try:
        return Decimal(str(val).strip())
    except InvalidOperation:
        return None


def find_location(session, client_id, site_name: str):
    key = site_name.strip().lower()
    rows = session.execute(
        select(Location)
        .where(Location.client_id == client_id)
        .where(Location.is_active.is_(True)),
    ).scalars().all()
    for loc in rows:
        if loc.site_name.strip().lower() == key:
            return loc
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-name", default="Apache", help="Client name in DB")
    parser.add_argument("--csv-path", type=Path, default=CSV_PATH)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.csv_path.exists():
        print(f"CSV not found: {args.csv_path}")
        sys.exit(1)

    engine = create_engine(settings.database_url_sync)
    Session = sessionmaker(bind=engine)
    session = Session()

    created_loc = 0
    updated_loc = 0
    job_codes_created = 0
    skipped = 0

    try:
        client = session.execute(select(Client).where(Client.name == args.client_name)).scalar_one_or_none()
        if not client:
            print(f"Client '{args.client_name}' not found")
            sys.exit(1)

        with args.csv_path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                site_name = (row.get("site_name") or "").strip()
                if not site_name:
                    skipped += 1
                    continue
                api_number = (row.get("api_number") or "").strip() or None
                lat = to_decimal(row.get("latitude"))
                lng = to_decimal(row.get("longitude"))
                county = (row.get("county") or "").strip()
                state = (row.get("state") or "").strip()
                region = ", ".join(p for p in (county, state) if p) or None
                job_code_list = split_job_codes(row.get("job_codes"))

                if lat is None or lng is None:
                    skipped += 1
                    continue

                loc = find_location(session, client.id, site_name)
                if not loc and api_number:
                    loc = session.execute(
                        select(Location)
                        .where(Location.client_id == client.id)
                        .where(Location.site_code == api_number),
                    ).scalar_one_or_none()

                if not loc:
                    if args.dry_run:
                        print(f"[dry-run] would create: {site_name!r} region={region!r}")
                        created_loc += 1
                        continue
                    loc = Location(
                        company_id=client.company_id,
                        client_id=client.id,
                        region=region,
                        site_name=site_name,
                        site_code=api_number,
                        latitude=lat,
                        longitude=lng,
                        is_active=True,
                    )
                    session.add(loc)
                    session.flush()
                    created_loc += 1
                else:
                    if not args.dry_run:
                        loc.latitude = lat
                        loc.longitude = lng
                        if api_number:
                            loc.site_code = api_number
                    updated_loc += 1

                if not args.dry_run:
                    for code in job_code_list:
                        existing_jc = session.execute(
                            select(JobCode)
                            .where(JobCode.location_id == loc.id)
                            .where(JobCode.code == code),
                        ).scalar_one_or_none()
                        if not existing_jc:
                            session.add(
                                JobCode(
                                    company_id=loc.company_id,
                                    location_id=loc.id,
                                    code=code,
                                    description=None,
                                    is_active=True,
                                ),
                            )
                            job_codes_created += 1

        if args.dry_run:
            session.rollback()
        else:
            session.commit()

        print(
            f"Done. created_locations={created_loc} updated_locations={updated_loc} "
            f"job_codes_added={job_codes_created} skipped_rows={skipped} dry_run={args.dry_run}",
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()
