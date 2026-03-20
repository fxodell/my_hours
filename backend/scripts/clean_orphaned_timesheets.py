"""
Remove invalid or clutter timesheets:
- Orphaned: pay_period or employee no longer exists
- Duplicates: same (employee_id, pay_period_id) - keep newest
- Empty old drafts: draft, no entries, pay period ended >60 days ago

Usage:
  From repo root:  python backend/scripts/clean_orphaned_timesheets.py
  Docker:          docker compose exec backend python scripts/clean_orphaned_timesheets.py
"""
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
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip("'\"")
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

from datetime import date, timedelta

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.core.database import SyncSessionLocal
from app.models import Timesheet, PayPeriod, Employee, TimeEntry, PTOEntry


def main():
    with SyncSessionLocal() as session:
        to_delete = {}

        # 1) Orphaned: timesheets whose pay_period or employee no longer exists
        result = session.execute(
            select(Timesheet).where(
                ~Timesheet.pay_period_id.in_(select(PayPeriod.id))
            )
        )
        for ts in result.scalars().all():
            to_delete[ts.id] = ("orphan_period", ts)
        result = session.execute(
            select(Timesheet).where(
                ~Timesheet.employee_id.in_(select(Employee.id))
            )
        )
        for ts in result.scalars().all():
            to_delete[ts.id] = ("orphan_employee", ts)

        # 2) Duplicates: same (employee_id, pay_period_id) - keep newest, remove rest
        dupes = session.execute(
            select(Timesheet.employee_id, Timesheet.pay_period_id)
            .group_by(Timesheet.employee_id, Timesheet.pay_period_id)
            .having(func.count(Timesheet.id) > 1)
        ).all()

        for (employee_id, pay_period_id) in dupes:
            rows = session.execute(
                select(Timesheet)
                .where(Timesheet.employee_id == employee_id, Timesheet.pay_period_id == pay_period_id)
                .order_by(Timesheet.created_at.desc())
            ).scalars().all()
            for ts in rows[1:]:  # keep first (newest), delete rest
                to_delete[ts.id] = ("duplicate", ts)

        # 3) Empty old drafts: draft, no time/pto entries, pay period ended >60 days ago
        cutoff = date.today() - timedelta(days=60)
        result = session.execute(
            select(Timesheet)
            .join(PayPeriod, Timesheet.pay_period_id == PayPeriod.id)
            .where(Timesheet.status == "draft")
            .where(PayPeriod.end_date < cutoff)
            .options(
                selectinload(Timesheet.time_entries),
                selectinload(Timesheet.pto_entries),
            )
        )
        for ts in result.scalars().all():
            if len(ts.time_entries) == 0 and len(ts.pto_entries) == 0:
                to_delete[ts.id] = ("empty_old_draft", ts)

        if not to_delete:
            print("No timesheets to remove (no orphans, duplicates, or empty old drafts).")
            return

        for tid, (reason, ts) in to_delete.items():
            if reason == "orphan_period":
                print(f"Deleting orphaned timesheet {tid} (missing pay period)")
            elif reason == "orphan_employee":
                print(f"Deleting orphaned timesheet {tid} (missing employee)")
            elif reason == "duplicate":
                print(f"Deleting duplicate timesheet {tid} (employee={ts.employee_id}, pay_period={ts.pay_period_id})")
            else:
                print(f"Deleting empty old draft timesheet {tid} (pay period ended before {cutoff})")
            session.delete(ts)

        session.commit()
        print(f"Removed {len(to_delete)} timesheet(s).")


if __name__ == "__main__":
    main()
