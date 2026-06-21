"""
Ensure open weekly pay periods exist for all active companies (groups A and B).

Idempotent: skips periods that already exist for a company/group/start date.
Intended to run daily via cron so the current week is always available.

Usage:
  From repo root:  python backend/scripts/generate_pay_periods.py
  Docker:          docker compose exec backend python scripts/generate_pay_periods.py
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta
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

from sqlalchemy import select

from app.core.database import SyncSessionLocal
from app.models.company import Company
from app.models.pay_period import PayPeriod

PERIOD_GROUPS = ("A", "B")
DEFAULT_WEEKS = 8


def monday_of_week(day: date) -> date:
    return day - timedelta(days=day.weekday())


def ensure_pay_periods(session, company: Company, start_date: date, weeks: int) -> list[PayPeriod]:
    created: list[PayPeriod] = []

    for period_group in PERIOD_GROUPS:
        for i in range(weeks):
            period_start = start_date + timedelta(days=7 * i)
            period_end = period_start + timedelta(days=6)

            existing = session.execute(
                select(PayPeriod).where(
                    PayPeriod.company_id == company.id,
                    PayPeriod.start_date == period_start,
                    PayPeriod.period_group == period_group,
                )
            ).scalar_one_or_none()

            if existing:
                continue

            pay_period = PayPeriod(
                company_id=company.id,
                period_group=period_group,
                start_date=period_start,
                end_date=period_end,
                status="open",
            )
            session.add(pay_period)
            created.append(pay_period)

    return created


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate missing weekly pay periods.")
    parser.add_argument(
        "--weeks",
        type=int,
        default=int(os.environ.get("PAY_PERIOD_WEEKS", DEFAULT_WEEKS)),
        help=f"Number of weekly periods to ensure from the current Monday (default: {DEFAULT_WEEKS})",
    )
    args = parser.parse_args()

    if args.weeks < 1:
        print("ERROR --weeks must be at least 1", file=sys.stderr)
        return 1

    start_date = monday_of_week(date.today())
    total_created = 0

    with SyncSessionLocal() as session:
        companies = list(
            session.execute(select(Company).where(Company.is_active.is_(True)).order_by(Company.name))
            .scalars()
            .all()
        )

        if not companies:
            print("No active companies found")
            return 0

        for company in companies:
            created = ensure_pay_periods(session, company, start_date, args.weeks)
            if created:
                session.commit()
                for period in created:
                    print(
                        f"Created {company.slug} group {period.period_group}: "
                        f"{period.start_date} to {period.end_date}"
                    )
                total_created += len(created)
            else:
                print(f"Up to date: {company.slug} ({args.weeks} weeks from {start_date})")

    print(f"Done. Created {total_created} pay period(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
