"""
Run the timesheet list query (same order as GET /api/timesheets) and print results.
Usage: cd backend && python scripts/query_timesheets_list.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import SyncSessionLocal
from app.models.timesheet import Timesheet
from app.models.pay_period import PayPeriod
from app.models.employee import Employee

if __name__ == "__main__":
    with SyncSessionLocal() as session:
        query = (
            select(Timesheet)
            .join(PayPeriod, Timesheet.pay_period_id == PayPeriod.id)
            .join(Employee, Timesheet.employee_id == Employee.id)
            .options(
                selectinload(Timesheet.employee),
                selectinload(Timesheet.pay_period),
            )
            .order_by(
                PayPeriod.start_date.desc(),
                Employee.last_name,
                Employee.first_name,
            )
        )
        result = session.execute(query)
        rows = result.unique().scalars().all()

    print(f"Timesheets (order: pay period desc, then employee last_name, first_name). Total: {len(rows)}\n")
    for i, ts in enumerate(rows, 1):
        emp = ts.employee
        pp = ts.pay_period
        print(f"{i}. {emp.full_name if emp else '?'}  |  {pp.start_date} – {pp.end_date}  |  {ts.status}")
    sys.exit(0)
