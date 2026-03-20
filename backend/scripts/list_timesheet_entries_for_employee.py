"""
List timesheet(s) and ALL time/pto entries for an employee (by first name).
Use to find out-of-period entries. No .env loading - run from repo root with PYTHONPATH.
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
from app.models import Timesheet, PayPeriod, Employee, TimeEntry, PTOEntry

def main():
    first_name = (sys.argv[1] or "Michael").strip()
    with SyncSessionLocal() as session:
        emp = session.execute(select(Employee).where(Employee.first_name.ilike(f"%{first_name}%"))).scalars().first()
        if not emp:
            print(f"No employee found matching '{first_name}'")
            return
        print(f"Employee: {emp.id} {emp.first_name} {emp.last_name} {emp.email}")
        # Timesheets with pay period
        rows = session.execute(
            select(Timesheet, PayPeriod)
            .join(PayPeriod, Timesheet.pay_period_id == PayPeriod.id)
            .where(Timesheet.employee_id == emp.id)
            .order_by(PayPeriod.start_date.desc())
            .limit(10)
        ).all()
        for ts, pp in rows:
            print(f"\nTimesheet {ts.id} status={ts.status}  pay_period: {pp.start_date} to {pp.end_date}")
            all_te = session.execute(select(TimeEntry).where(TimeEntry.timesheet_id == ts.id).order_by(TimeEntry.work_date)).scalars().all()
            all_pto = session.execute(select(PTOEntry).where(PTOEntry.timesheet_id == ts.id).order_by(PTOEntry.pto_date)).scalars().all()
            for e in all_te:
                in_range = pp.start_date <= e.work_date <= pp.end_date
                print(f"  time entry {e.id}  work_date={e.work_date}  hours={e.hours}  in_period={in_range}")
            for e in all_pto:
                in_range = pp.start_date <= e.pto_date <= pp.end_date
                print(f"  pto entry  {e.id}  pto_date={e.pto_date}   hours={e.hours}  in_period={in_range}")

def list_out_of_period():
    """List all time/pto entries with work_date Mar 9 or Mar 10 2026."""
    with SyncSessionLocal() as session:
        d9 = date(2026, 3, 9)
        d10 = date(2026, 3, 10)
        te = session.execute(
            select(TimeEntry, Timesheet, PayPeriod)
            .join(Timesheet, TimeEntry.timesheet_id == Timesheet.id)
            .join(PayPeriod, Timesheet.pay_period_id == PayPeriod.id)
            .where((TimeEntry.work_date == d9) | (TimeEntry.work_date == d10))
        ).all()
        pto = session.execute(
            select(PTOEntry, Timesheet, PayPeriod)
            .join(Timesheet, PTOEntry.timesheet_id == Timesheet.id)
            .join(PayPeriod, Timesheet.pay_period_id == PayPeriod.id)
            .where((PTOEntry.pto_date == d9) | (PTOEntry.pto_date == d10))
        ).all()
        print("Time entries on Mar 9 or Mar 10 2026:")
        for e, ts, pp in te:
            in_range = pp.start_date <= e.work_date <= pp.end_date
            print(f"  id={e.id} work_date={e.work_date} timesheet={ts.id} pay_period={pp.start_date} to {pp.end_date} in_period={in_range}")
        print("PTO entries on Mar 9 or Mar 10 2026:")
        for e, ts, pp in pto:
            in_range = pp.start_date <= e.pto_date <= pp.end_date
            print(f"  id={e.id} pto_date={e.pto_date} timesheet={ts.id} pay_period={pp.start_date} to {pp.end_date} in_period={in_range}")

def list_mar15_28_entries():
    """List ALL time entries for timesheets with pay period Mar 15-28 (any work_date)."""
    mar15 = date(2026, 3, 15)
    mar28 = date(2026, 3, 28)
    with SyncSessionLocal() as session:
        # Timesheets for pay period Mar 15 - Mar 28
        rows = session.execute(
            select(Timesheet, PayPeriod, Employee)
            .join(PayPeriod, Timesheet.pay_period_id == PayPeriod.id)
            .join(Employee, Timesheet.employee_id == Employee.id)
            .where(PayPeriod.start_date == mar15, PayPeriod.end_date == mar28)
        ).all()
        print(f"Timesheets with pay period Mar 15 - Mar 28, 2026:")
        for ts, pp, emp in rows:
            print(f"  timesheet={ts.id} status={ts.status} employee={emp.first_name} {emp.last_name}")
            entries = session.execute(select(TimeEntry).where(TimeEntry.timesheet_id == ts.id).order_by(TimeEntry.work_date)).scalars().all()
            for e in entries:
                out = " OUT_OF_PERIOD" if not (pp.start_date <= e.work_date <= pp.end_date) else ""
                print(f"    time entry {e.id} work_date={e.work_date} hours={e.hours}{out}")
            pto = session.execute(select(PTOEntry).where(PTOEntry.timesheet_id == ts.id).order_by(PTOEntry.pto_date)).scalars().all()
            for e in pto:
                out = " OUT_OF_PERIOD" if not (pp.start_date <= e.pto_date <= pp.end_date) else ""
                print(f"    pto entry  {e.id} pto_date={e.pto_date} hours={e.hours}{out}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--out-of-period":
        list_out_of_period()
    elif len(sys.argv) > 1 and sys.argv[1] == "--mar15-28":
        list_mar15_28_entries()
    else:
        main()
