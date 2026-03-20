"""
Remove time/PTO entries dated March 9 or March 10 2026 from timesheets
whose pay period is March 15 - March 28 2026. Safe to run multiple times.

Usage: From repo root:  PYTHONPATH=backend python backend/scripts/remove_mar9_mar10_from_mar15_28_timesheets.py
"""
import os
import sys
from pathlib import Path
from datetime import date

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

from sqlalchemy import select
from app.core.database import SyncSessionLocal
from app.models import Timesheet, PayPeriod, TimeEntry, PTOEntry

MAR15 = date(2026, 3, 15)
MAR28 = date(2026, 3, 28)
MAR9 = date(2026, 3, 9)
MAR10 = date(2026, 3, 10)

def main():
    with SyncSessionLocal() as session:
        # Timesheet IDs for pay period Mar 15 - Mar 28
        ts_ids = [
            row[0] for row in session.execute(
                select(Timesheet.id)
                .join(PayPeriod, Timesheet.pay_period_id == PayPeriod.id)
                .where(PayPeriod.start_date == MAR15, PayPeriod.end_date == MAR28)
            ).all()
        ]
        if not ts_ids:
            print("No timesheets found for pay period Mar 15 - Mar 28, 2026.")
            return

        # Time entries on Mar 9 or Mar 10 in those timesheets
        time_entries = session.execute(
            select(TimeEntry)
            .where(TimeEntry.timesheet_id.in_(ts_ids))
            .where((TimeEntry.work_date == MAR9) | (TimeEntry.work_date == MAR10))
        ).scalars().all()

        pto_entries = session.execute(
            select(PTOEntry)
            .where(PTOEntry.timesheet_id.in_(ts_ids))
            .where((PTOEntry.pto_date == MAR9) | (PTOEntry.pto_date == MAR10))
        ).scalars().all()

        if not time_entries and not pto_entries:
            print("No March 9 or March 10 entries found on any Mar 15-28 timesheet. Nothing to remove.")
            return

        for e in time_entries:
            print(f"Deleting time entry {e.id} work_date={e.work_date} timesheet={e.timesheet_id}")
            session.delete(e)
        for e in pto_entries:
            print(f"Deleting PTO entry {e.id} pto_date={e.pto_date} timesheet={e.timesheet_id}")
            session.delete(e)
        session.commit()
        print(f"Removed {len(time_entries)} time entries and {len(pto_entries)} PTO entries.")

if __name__ == "__main__":
    main()
