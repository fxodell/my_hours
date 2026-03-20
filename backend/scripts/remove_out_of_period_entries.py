"""
Remove time and PTO entries whose work_date/pto_date fall outside their
timesheet's pay period. Run once to clean up bad data.

Usage:
  From repo root:  python backend/scripts/remove_out_of_period_entries.py
  Docker:          docker compose exec backend python scripts/remove_out_of_period_entries.py
"""
import os
import sys
from pathlib import Path

# Project root (backend/scripts -> backend -> root)
_backend = Path(__file__).resolve().parent.parent
_root = _backend.parent
sys.path.insert(0, str(_backend))

# Load .env from project root; set only DATABASE_URL_SYNC so Settings has no extra vars
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

from sqlalchemy import select

from app.core.database import SyncSessionLocal
from app.models import TimeEntry, PTOEntry, Timesheet, PayPeriod


def main():
    with SyncSessionLocal() as session:
        # Time entries outside pay period
        result = session.execute(
            select(TimeEntry)
            .join(Timesheet, TimeEntry.timesheet_id == Timesheet.id)
            .join(PayPeriod, Timesheet.pay_period_id == PayPeriod.id)
            .where(
                (TimeEntry.work_date < PayPeriod.start_date)
                | (TimeEntry.work_date > PayPeriod.end_date)
            )
        )
        time_entries = result.scalars().all()

        # PTO entries outside pay period
        result = session.execute(
            select(PTOEntry)
            .join(Timesheet, PTOEntry.timesheet_id == Timesheet.id)
            .join(PayPeriod, Timesheet.pay_period_id == PayPeriod.id)
            .where(
                (PTOEntry.pto_date < PayPeriod.start_date)
                | (PTOEntry.pto_date > PayPeriod.end_date)
            )
        )
        pto_entries = result.scalars().all()

        if not time_entries and not pto_entries:
            print("No out-of-period entries found.")
            return

        for e in time_entries:
            print(f"Deleting time entry {e.id} (work_date={e.work_date}, timesheet={e.timesheet_id})")
            session.delete(e)
        for e in pto_entries:
            print(f"Deleting PTO entry {e.id} (pto_date={e.pto_date}, timesheet={e.timesheet_id})")
            session.delete(e)

        session.commit()
        print(f"Removed {len(time_entries)} time entries and {len(pto_entries)} PTO entries.")


if __name__ == "__main__":
    main()
