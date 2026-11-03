"""
Mirror Location.site_code into JobCode rows and link orphan time entries.

BNB (and some NFM) locations store AFE/site codes on Location.site_code without
a matching JobCode, so time entries were saved with location_id but null
job_code_id and exports left the Site Code column blank.

This script:
  1. Creates an active JobCode for each location that has site_code but no
     matching JobCode.code
  2. Sets TimeEntry.job_code_id when it is null and the location has a JobCode
     whose code matches Location.site_code (or the location has exactly one
     active JobCode)

Usage:
  From repo root:  python backend/scripts/backfill_site_codes_from_locations.py
  Docker:          docker compose exec backend python scripts/backfill_site_codes_from_locations.py
  Dry run:         ... --dry-run
  One company:     ... --company-slug bnb
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
_root = _backend.parent
sys.path.insert(0, str(_backend))

_env_file = _root / ".env"
if _env_file.exists():
    env = {}
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip().strip("'\"")
    url_sync = env.get("DATABASE_URL_SYNC")
    if not url_sync and all(env.get(k) for k in ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB")):
        host = env.get("POSTGRES_HOST", "localhost")
        url_sync = "postgresql+psycopg2://{user}:{pw}@{host}:5432/{db}".format(
            user=env["POSTGRES_USER"], pw=env["POSTGRES_PASSWORD"], host=host, db=env["POSTGRES_DB"]
        )
    if url_sync:
        os.environ["DATABASE_URL_SYNC"] = url_sync
    if env.get("DATABASE_URL"):
        os.environ["DATABASE_URL"] = env["DATABASE_URL"]

from sqlalchemy import select, func, update

from app.core.database import SyncSessionLocal
from app.models.company import Company
from app.models.job_code import JobCode
from app.models.location import Location
from app.models.time_entry import TimeEntry


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill JobCodes from Location.site_code")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without committing")
    parser.add_argument("--company-slug", type=str, default=None, help="Limit to one company slug")
    args = parser.parse_args()

    created_codes = 0
    reactivated = 0
    linked_entries = 0

    with SyncSessionLocal() as session:
        company_query = select(Company).where(Company.is_active.is_(True)).order_by(Company.slug)
        if args.company_slug:
            company_query = company_query.where(Company.slug == args.company_slug)
        companies = list(session.execute(company_query).scalars().all())
        if not companies:
            print("No matching companies found")
            return 1

        for company in companies:
            locations = list(
                session.execute(
                    select(Location).where(
                        Location.company_id == company.id,
                        Location.site_code.is_not(None),
                        Location.site_code != "",
                    )
                )
                .scalars()
                .all()
            )
            print(f"{company.slug}: {len(locations)} location(s) with site_code")

            for loc in locations:
                code = (loc.site_code or "").strip()
                if not code:
                    continue

                existing = session.execute(
                    select(JobCode).where(
                        JobCode.location_id == loc.id,
                        JobCode.code == code,
                    )
                ).scalar_one_or_none()

                if existing:
                    if not existing.is_active:
                        existing.is_active = True
                        reactivated += 1
                    job_code = existing
                else:
                    job_code = JobCode(
                        company_id=loc.company_id,
                        location_id=loc.id,
                        code=code,
                        description=loc.site_name,
                        is_active=True,
                    )
                    session.add(job_code)
                    session.flush()
                    created_codes += 1

                # Link orphan entries that match this location.site_code
                result = session.execute(
                    update(TimeEntry)
                    .where(
                        TimeEntry.location_id == loc.id,
                        TimeEntry.job_code_id.is_(None),
                    )
                    .values(job_code_id=job_code.id)
                )
                linked_entries += result.rowcount or 0

            # Also link orphans on locations with exactly one active job code
            # (even if Location.site_code is empty / mismatched)
            single_jc_locs = session.execute(
                select(JobCode.location_id, func.count())
                .where(JobCode.company_id == company.id, JobCode.is_active.is_(True))
                .group_by(JobCode.location_id)
                .having(func.count() == 1)
            ).all()
            for location_id, _count in single_jc_locs:
                jc = session.execute(
                    select(JobCode).where(
                        JobCode.location_id == location_id,
                        JobCode.is_active.is_(True),
                    )
                ).scalar_one()
                result = session.execute(
                    update(TimeEntry)
                    .where(
                        TimeEntry.location_id == location_id,
                        TimeEntry.job_code_id.is_(None),
                    )
                    .values(job_code_id=jc.id)
                )
                linked_entries += result.rowcount or 0

        if args.dry_run:
            session.rollback()
            print(
                f"[dry-run] would create {created_codes} job code(s), "
                f"reactivate {reactivated}, link {linked_entries} entr(y/ies)"
            )
        else:
            session.commit()
            print(
                f"Created {created_codes} job code(s), reactivated {reactivated}, "
                f"linked {linked_entries} entr(y/ies)"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
