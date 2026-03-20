from datetime import date, timedelta
from io import BytesIO
from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
import pandas as pd

from app.models.timesheet import Timesheet
from app.models.time_entry import TimeEntry
from app.models.pto_entry import PTOEntry
from app.models.employee import Employee
from app.models.client import Client
from app.models.service_type import ServiceType
from app.models.pay_period import PayPeriod
from app.api.deps import DB, CurrentUser, CurrentManager

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/payroll")
async def payroll_report(
    db: DB,
    current_user: CurrentManager,
    pay_period_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    format: str = "json",  # json, csv, excel
):
    """
    Generate payroll report for approved timesheets.
    Can filter by pay period or date range.
    Export as JSON, CSV, or Excel.
    """
    # Build query for approved timesheets
    query = (
        select(Timesheet)
        .join(PayPeriod, Timesheet.pay_period_id == PayPeriod.id)
        .where(Timesheet.status == "approved")
        .options(
            selectinload(Timesheet.employee),
            selectinload(Timesheet.pay_period),
            selectinload(Timesheet.time_entries),
            selectinload(Timesheet.pto_entries),
        )
    )

    if pay_period_id:
        query = query.where(Timesheet.pay_period_id == pay_period_id)
    if start_date:
        query = query.where(PayPeriod.end_date >= start_date)
    if end_date:
        query = query.where(PayPeriod.start_date <= end_date)

    result = await db.execute(query)
    timesheets = result.unique().scalars().all()

    # Build report data
    report_data = []
    for ts in timesheets:

        work_hours = sum(float(e.hours) for e in ts.time_entries)
        pto_hours = sum(float(e.hours) for e in ts.pto_entries)
        overtime_hours = sum(float(e.hours) for e in ts.time_entries if e.is_overtime)
        regular_hours = work_hours - overtime_hours

        # Calculate by PTO type
        pto_by_type = {}
        for pto in ts.pto_entries:
            pto_by_type[pto.pto_type] = pto_by_type.get(pto.pto_type, 0) + float(pto.hours)

        report_data.append({
            "employee_id": str(ts.employee.id),
            "employee_name": ts.employee.full_name,
            "employee_email": ts.employee.email,
            "engage_id": ts.employee.engage_employee_id or "",
            "pay_period_start": ts.pay_period.start_date.isoformat(),
            "pay_period_end": ts.pay_period.end_date.isoformat(),
            "pay_period_group": ts.pay_period.period_group,
            "regular_hours": regular_hours,
            "overtime_hours": overtime_hours,
            "total_work_hours": work_hours,
            "personal_pto_hours": pto_by_type.get("personal", 0),
            "sick_pto_hours": pto_by_type.get("sick", 0),
            "holiday_hours": pto_by_type.get("holiday", 0),
            "other_pto_hours": pto_by_type.get("other", 0),
            "total_pto_hours": pto_hours,
            "total_hours": work_hours + pto_hours,
            "approved_at": ts.approved_at.isoformat() if ts.approved_at else "",
        })

    if format == "json":
        return {"report": "payroll", "data": report_data}

    # Create DataFrame for export
    df = pd.DataFrame(report_data)

    if format == "csv":
        output = BytesIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=payroll_report.csv"},
        )

    if format == "excel":
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Payroll", index=False)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=payroll_report.xlsx"},
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid format. Use json, csv, or excel.",
    )


@router.get("/billing")
async def billing_report(
    db: DB,
    current_user: CurrentManager,
    client_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    format: str = "json",
):
    """
    Generate billing report by client for invoicing.
    Groups hours by client, employee, service type, and date.
    """
    # Get all approved time entries
    query = (
        select(TimeEntry)
        .join(Timesheet)
        .where(Timesheet.status == "approved")
        .where(TimeEntry.is_billable == True)
        .options(
            selectinload(TimeEntry.timesheet).selectinload(Timesheet.employee),
            selectinload(TimeEntry.client),
            selectinload(TimeEntry.location),
            selectinload(TimeEntry.job_code),
            selectinload(TimeEntry.service_type),
        )
    )

    if client_id:
        query = query.where(TimeEntry.client_id == client_id)

    if start_date:
        query = query.where(TimeEntry.work_date >= start_date)

    if end_date:
        query = query.where(TimeEntry.work_date <= end_date)

    query = query.order_by(TimeEntry.work_date)

    result = await db.execute(query)
    entries = result.scalars().all()

    report_data = []
    for entry in entries:
        location_display = "Unassigned"
        if entry.location:
            location_display = (
                f"{entry.location.site_name} ({entry.location.region})"
                if entry.location.region
                else entry.location.site_name
            )
        site_code = entry.job_code.code if entry.job_code else "—"
        report_data.append({
            "date": entry.work_date.isoformat(),
            "client": entry.client.name if entry.client else "Unassigned",
            "location": location_display,
            "site_code": site_code,
            "employee": entry.timesheet.employee.full_name,
            "service_type": entry.service_type.name if entry.service_type else "General",
            "hours": float(entry.hours),
            "work_mode": entry.work_mode,
            "description": entry.description or "",
        })

    if format == "json":
        # Also provide summary by client
        summary = {}
        for row in report_data:
            client = row["client"]
            if client not in summary:
                summary[client] = {"hours": 0, "bonus_hours": 0}
            summary[client]["hours"] += row["hours"]

        return {
            "report": "billing",
            "summary": summary,
            "data": report_data,
        }

    df = pd.DataFrame(report_data)

    if format == "csv":
        output = BytesIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=billing_report.csv"},
        )

    if format == "excel":
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Billing Detail", index=False)

            # Add summary sheet
            summary_data = []
            clients_seen = set()
            for row in report_data:
                if row["client"] not in clients_seen:
                    clients_seen.add(row["client"])

            for client in clients_seen:
                client_rows = [r for r in report_data if r["client"] == client]
                total = sum(r["hours"] for r in client_rows)
                summary_data.append({
                    "Client": client,
                    "Total Hours": total,
                    "Bonus Hours": 0,
                })

            pd.DataFrame(summary_data).to_excel(
                writer, sheet_name="Summary by Client", index=False
            )

        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=billing_report.xlsx"},
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid format. Use json, csv, or excel.",
    )


@router.get("/hours-by-employee")
async def hours_by_employee(
    db: DB,
    current_user: CurrentManager,
    start_date: date | None = None,
    end_date: date | None = None,
    format: str = "json",
):
    """
    Report showing total hours per employee.
    """
    query = (
        select(
            Employee.id,
            Employee.first_name,
            Employee.last_name,
            Employee.email,
            func.sum(TimeEntry.hours).label("total_hours"),
        )
        .join(Timesheet, Timesheet.employee_id == Employee.id)
        .join(TimeEntry, TimeEntry.timesheet_id == Timesheet.id)
        .where(Timesheet.status == "approved")
        .group_by(Employee.id)
        .order_by(Employee.last_name, Employee.first_name)
    )

    if start_date:
        query = query.where(TimeEntry.work_date >= start_date)
    if end_date:
        query = query.where(TimeEntry.work_date <= end_date)

    result = await db.execute(query)
    rows = result.all()

    report_data = [
        {
            "employee_id": str(row.id),
            "employee_name": f"{row.first_name} {row.last_name}",
            "email": row.email,
            "total_hours": float(row.total_hours) if row.total_hours else 0,
        }
        for row in rows
    ]

    if format == "json":
        return {"report": "hours_by_employee", "data": report_data}

    df = pd.DataFrame(report_data)

    if format == "csv":
        output = BytesIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=hours_by_employee.csv"},
        )

    if format == "excel":
        output = BytesIO()
        df.to_excel(output, sheet_name="Hours by Employee", index=False)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=hours_by_employee.xlsx"},
        )

    raise HTTPException(status_code=400, detail="Invalid format")


@router.get("/hours-by-job-code")
async def hours_by_job_code(
    db: DB,
    current_user: CurrentManager,
    client_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    format: str = "json",
):
    """
    Report showing hours grouped by client and service type (as proxy for job code).
    """
    query = (
        select(TimeEntry)
        .join(Timesheet)
        .where(Timesheet.status == "approved")
        .options(
            selectinload(TimeEntry.client),
            selectinload(TimeEntry.service_type),
            selectinload(TimeEntry.job_code),
        )
    )

    if client_id:
        query = query.where(TimeEntry.client_id == client_id)
    if start_date:
        query = query.where(TimeEntry.work_date >= start_date)
    if end_date:
        query = query.where(TimeEntry.work_date <= end_date)

    result = await db.execute(query)
    entries = result.scalars().all()

    # Group by client + service type
    grouped = {}
    for entry in entries:
        client_name = entry.client.name if entry.client else "Unassigned"
        service_name = entry.service_type.name if entry.service_type else "General"
        job_code = entry.job_code.code if entry.job_code else "N/A"
        key = (client_name, service_name, job_code)

        if key not in grouped:
            grouped[key] = 0
        grouped[key] += float(entry.hours)

    report_data = [
        {
            "client": k[0],
            "service_type": k[1],
            "job_code": k[2],
            "total_hours": v,
        }
        for k, v in sorted(grouped.items())
    ]

    if format == "json":
        return {"report": "hours_by_job_code", "data": report_data}

    df = pd.DataFrame(report_data)

    if format == "csv":
        output = BytesIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=hours_by_job_code.csv"},
        )

    if format == "excel":
        output = BytesIO()
        df.to_excel(output, sheet_name="Hours by Job Code", index=False)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=hours_by_job_code.xlsx"},
        )

    raise HTTPException(status_code=400, detail="Invalid format")


@router.get("/engage-export")
async def engage_payroll_export(
    db: DB,
    current_user: CurrentManager,
    pay_period_id: UUID,
):
    """
    Generate payroll export formatted for Engage payroll system.

    Exports a CSV with columns formatted for Engage import:
    - Employee ID (Engage ID)
    - Employee Name
    - Pay Period Start
    - Pay Period End
    - Regular Hours
    - Overtime Hours
    - PTO Hours (broken down by type)
    - Vehicle Reimbursement
    - Bonus Amount
    """
    # Get pay period info
    period_result = await db.execute(
        select(PayPeriod).where(PayPeriod.id == pay_period_id)
    )
    pay_period = period_result.scalar_one_or_none()

    if not pay_period:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pay period not found"
        )

    # Get approved timesheets for this pay period
    query = (
        select(Timesheet)
        .where(Timesheet.pay_period_id == pay_period_id)
        .where(Timesheet.status == "approved")
        .options(
            selectinload(Timesheet.employee),
            selectinload(Timesheet.time_entries).selectinload(TimeEntry.client),
            selectinload(Timesheet.pto_entries),
        )
    )

    result = await db.execute(query)
    timesheets = result.scalars().all()

    # Build Engage-formatted data
    engage_data = []

    for ts in timesheets:
        employee = ts.employee

        # Calculate hours
        regular_hours = 0
        overtime_hours = 0
        bonus_hours = 0
        vehicle_reimbursement = 0

        for entry in ts.time_entries:
            hours = float(entry.hours)
            if entry.is_overtime:
                overtime_hours += hours
            else:
                regular_hours += hours

            # Parse vehicle reimbursement tier
            if entry.vehicle_reimbursement_tier:
                tier = entry.vehicle_reimbursement_tier
                if "$30" in tier:
                    vehicle_reimbursement += 30
                elif "$60" in tier:
                    vehicle_reimbursement += 60
                elif "$90" in tier:
                    vehicle_reimbursement += 90
                elif "$120" in tier:
                    vehicle_reimbursement += 120

        # PTO hours by type
        pto_personal = sum(float(p.hours) for p in ts.pto_entries if p.pto_type == "personal")
        pto_sick = sum(float(p.hours) for p in ts.pto_entries if p.pto_type == "sick")
        pto_holiday = sum(float(p.hours) for p in ts.pto_entries if p.pto_type == "holiday")
        pto_other = sum(float(p.hours) for p in ts.pto_entries if p.pto_type == "other")

        # Bonus is deprecated; kept for export schema compatibility
        bonus_amount = bonus_hours * 5

        engage_data.append({
            "EngageEmployeeID": employee.engage_employee_id or "",
            "EmployeeName": employee.full_name,
            "Email": employee.email,
            "PayPeriodStart": pay_period.start_date.strftime("%m/%d/%Y"),
            "PayPeriodEnd": pay_period.end_date.strftime("%m/%d/%Y"),
            "RegularHours": regular_hours,
            "OvertimeHours": overtime_hours,
            "TotalWorkHours": regular_hours + overtime_hours,
            "PersonalPTO": pto_personal,
            "SickPTO": pto_sick,
            "HolidayPTO": pto_holiday,
            "OtherPTO": pto_other,
            "TotalPTO": pto_personal + pto_sick + pto_holiday + pto_other,
            "TotalHours": regular_hours + overtime_hours + pto_personal + pto_sick + pto_holiday + pto_other,
            "VehicleReimbursement": vehicle_reimbursement,
            "BonusHours": bonus_hours,
            "BonusAmount": bonus_amount,
        })

    # Sort by employee name
    engage_data.sort(key=lambda x: x["EmployeeName"])

    # Generate CSV
    df = pd.DataFrame(engage_data)

    output = BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)

    filename = f"engage_payroll_{pay_period.start_date}_{pay_period.end_date}.csv"

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def _timesheet_totals(ts: Timesheet) -> dict:
    """Extract aggregate totals from a single timesheet (shared helper)."""
    work_hours = sum(float(e.hours) for e in ts.time_entries)
    pto_hours = sum(float(e.hours) for e in ts.pto_entries)
    overtime_hours = sum(float(e.hours) for e in ts.time_entries if e.is_overtime)
    regular_hours = work_hours - overtime_hours

    pto_by_type: dict[str, float] = {}
    for pto in ts.pto_entries:
        pto_by_type[pto.pto_type] = pto_by_type.get(pto.pto_type, 0) + float(pto.hours)

    return {
        "regular_hours": regular_hours,
        "overtime_hours": overtime_hours,
        "total_work_hours": work_hours,
        "personal_pto_hours": pto_by_type.get("personal", 0),
        "sick_pto_hours": pto_by_type.get("sick", 0),
        "holiday_hours": pto_by_type.get("holiday", 0),
        "other_pto_hours": pto_by_type.get("other", 0),
        "total_pto_hours": pto_hours,
        "total_hours": work_hours + pto_hours,
    }


@router.get("/payroll-biweekly")
async def payroll_biweekly_report(
    db: DB,
    current_user: CurrentManager,
    period_group: str,
    anchor_start_date: date,
    format: str = "json",
):
    """
    Biweekly payroll rollup — one row per employee for two consecutive
    weekly pay periods.

    Parameters:
        period_group: 'A' or 'B'
        anchor_start_date: The Sunday starting the first of the two weekly periods.
        format: json | csv | excel

    The server loads exactly two consecutive periods for the given group
    starting at anchor_start_date. Returns 400 if either period is missing
    or they are not consecutive weeks.
    """
    if period_group not in ("A", "B"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="period_group must be 'A' or 'B'",
        )

    # Load the two consecutive weekly periods for this group
    result = await db.execute(
        select(PayPeriod)
        .where(PayPeriod.period_group == period_group)
        .where(PayPeriod.start_date >= anchor_start_date)
        .order_by(PayPeriod.start_date.asc())
        .limit(2)
    )
    periods = list(result.scalars().all())

    if len(periods) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not find two pay periods for the given group starting at anchor_start_date",
        )

    week1, week2 = periods[0], periods[1]

    if week1.start_date != anchor_start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No pay period starts on {anchor_start_date} for group {period_group}",
        )

    # Validate consecutive: week2 should start the day after week1 ends
    expected_week2_start = week1.end_date + timedelta(days=1)
    if week2.start_date != expected_week2_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Periods are not consecutive: week 1 ends {week1.end_date}, week 2 starts {week2.start_date}",
        )

    biweekly_start = week1.start_date
    biweekly_end = week2.end_date

    # Build list of all 14 dates
    num_days = (biweekly_end - biweekly_start).days + 1
    all_dates = [biweekly_start + timedelta(days=i) for i in range(num_days)]
    date_keys = [d.isoformat() for d in all_dates]

    # Load approved timesheets for both periods, filtered to matching group employees
    period_ids = [week1.id, week2.id]
    result = await db.execute(
        select(Timesheet)
        .where(Timesheet.pay_period_id.in_(period_ids))
        .where(Timesheet.status == "approved")
        .options(
            selectinload(Timesheet.employee),
            selectinload(Timesheet.pay_period),
            selectinload(Timesheet.time_entries),
            selectinload(Timesheet.pto_entries),
        )
    )
    all_timesheets = result.unique().scalars().all()

    # Filter to employees whose pay_period_group matches; track warnings
    data_quality_warnings: list[str] = []
    timesheets = []
    for ts in all_timesheets:
        if not ts.employee:
            continue
        if ts.employee.pay_period_group != period_group:
            data_quality_warnings.append(
                f"Excluded timesheet {ts.id} for {ts.employee.full_name} "
                f"(employee group {ts.employee.pay_period_group} != report group {period_group})"
            )
            continue
        timesheets.append(ts)

    # Group timesheets by employee
    by_employee: dict[str, list[Timesheet]] = {}
    for ts in timesheets:
        eid = str(ts.employee_id)
        by_employee.setdefault(eid, []).append(ts)

    # Build report rows
    report_data = []
    for eid, emp_timesheets in by_employee.items():
        emp = emp_timesheets[0].employee

        # Aggregate totals across both weeks
        agg = {
            "regular_hours": 0.0,
            "overtime_hours": 0.0,
            "total_work_hours": 0.0,
            "personal_pto_hours": 0.0,
            "sick_pto_hours": 0.0,
            "holiday_hours": 0.0,
            "other_pto_hours": 0.0,
            "total_pto_hours": 0.0,
            "total_hours": 0.0,
        }
        for ts in emp_timesheets:
            totals = _timesheet_totals(ts)
            for k in agg:
                agg[k] += totals[k]

        # Build per-day hours (work + PTO combined)
        hours_by_date: dict[str, float] = {dk: 0.0 for dk in date_keys}
        for ts in emp_timesheets:
            for entry in ts.time_entries:
                dk = entry.work_date.isoformat()
                if dk in hours_by_date:
                    hours_by_date[dk] += float(entry.hours)
            for pto in ts.pto_entries:
                dk = pto.pto_date.isoformat()
                if dk in hours_by_date:
                    hours_by_date[dk] += float(pto.hours)

        period_total_hours = sum(hours_by_date.values())

        # Determine which weeks are present
        week_ids = {str(ts.pay_period_id) for ts in emp_timesheets}
        weeks_count = len(week_ids)
        missing_weeks = []
        if str(week1.id) not in week_ids:
            missing_weeks.append(1)
        if str(week2.id) not in week_ids:
            missing_weeks.append(2)

        row = {
            "employee_id": eid,
            "employee_name": emp.full_name,
            "employee_email": emp.email,
            "engage_id": emp.engage_employee_id or "",
            "period_group": period_group,
            "biweekly_start": biweekly_start.isoformat(),
            "biweekly_end": biweekly_end.isoformat(),
            "week_1_pay_period_id": str(week1.id),
            "week_2_pay_period_id": str(week2.id),
            "weeks_count": weeks_count,
            "missing_weeks": missing_weeks,
            **agg,
            "period_total_hours": period_total_hours,
            "hours_by_date": hours_by_date,
        }
        report_data.append(row)

    # Sort by employee name
    report_data.sort(key=lambda r: r["employee_name"])

    if format == "json":
        resp = {
            "report": "payroll_biweekly",
            "period_group": period_group,
            "biweekly_start": biweekly_start.isoformat(),
            "biweekly_end": biweekly_end.isoformat(),
            "week_1_pay_period_id": str(week1.id),
            "week_2_pay_period_id": str(week2.id),
            "data": report_data,
        }
        if data_quality_warnings:
            resp["data_quality_warnings"] = data_quality_warnings
        return resp

    # Flatten hours_by_date into columns for CSV/Excel
    flat_rows = []
    for row in report_data:
        flat = {k: v for k, v in row.items() if k not in ("hours_by_date", "missing_weeks")}
        flat["missing_weeks"] = ",".join(str(w) for w in row["missing_weeks"]) if row["missing_weeks"] else ""
        for dk in date_keys:
            flat[dk] = row["hours_by_date"][dk]
        flat_rows.append(flat)

    df = pd.DataFrame(flat_rows)

    if format == "csv":
        output = BytesIO()
        df.to_csv(output, index=False)
        output.seek(0)
        filename = f"payroll_biweekly_{period_group}_{biweekly_start}_{biweekly_end}.csv"
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    if format == "excel":
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Biweekly Payroll", index=False)
        output.seek(0)
        filename = f"payroll_biweekly_{period_group}_{biweekly_start}_{biweekly_end}.xlsx"
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid format. Use json, csv, or excel.",
    )


# ---------------------------------------------------------------------------
# Shared helper for employee-detail and my-time-detail reports
# ---------------------------------------------------------------------------

_MAX_DATE_SPAN_DAYS = 366
_MAX_EMPLOYEES_PER_REQUEST = 50
_VALID_TIMESHEET_STATUSES = {"draft", "submitted", "approved", "rejected"}


def _parse_statuses(raw: str | None) -> set[str] | None:
    """Parse comma-separated status filter. Returns None for 'all'."""
    if not raw or raw.strip().lower() == "all":
        return None  # no filter
    statuses = {s.strip().lower() for s in raw.split(",")}
    invalid = statuses - _VALID_TIMESHEET_STATUSES
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid timesheet_status values: {', '.join(sorted(invalid))}. "
                   f"Valid: {', '.join(sorted(_VALID_TIMESHEET_STATUSES))}, all",
        )
    return statuses


def _build_entry_row(entry: TimeEntry, ts: Timesheet, emp: Employee, pp: PayPeriod) -> dict:
    """Build one output row for a TimeEntry."""
    return {
        "entry_kind": "work",
        "work_date": entry.work_date.isoformat(),
        "employee_id": str(emp.id),
        "employee_name": emp.full_name,
        "client": entry.client.name if entry.client else "Unassigned",
        "location": entry.location.site_name if entry.location else "Unassigned",
        "region": entry.location.region if entry.location and entry.location.region else "",
        "site_code": entry.job_code.code if entry.job_code else "",
        "job_code_description": entry.job_code.description if entry.job_code else "",
        "service_type": entry.service_type.name if entry.service_type else "",
        "work_mode": entry.work_mode,
        "hours": float(entry.hours),
        "description": entry.description or "",
        "is_billable": entry.is_billable,
        "is_overtime": entry.is_overtime,
        "start_time": entry.start_time.isoformat() if entry.start_time else "",
        "end_time": entry.end_time.isoformat() if entry.end_time else "",
        "vehicle_reimbursement_tier": entry.vehicle_reimbursement_tier or "",
        "pto_type": "",
        "timesheet_id": str(ts.id),
        "timesheet_status": ts.status,
        "pay_period_start": pp.start_date.isoformat(),
        "pay_period_end": pp.end_date.isoformat(),
        "period_group": pp.period_group,
    }


def _build_pto_row(pto: PTOEntry, ts: Timesheet, emp: Employee, pp: PayPeriod) -> dict:
    """Build one output row for a PTOEntry."""
    return {
        "entry_kind": "pto",
        "work_date": pto.pto_date.isoformat(),
        "employee_id": str(emp.id),
        "employee_name": emp.full_name,
        "client": "",
        "location": "",
        "region": "",
        "site_code": "",
        "job_code_description": "",
        "service_type": "",
        "work_mode": "",
        "hours": float(pto.hours),
        "description": pto.notes or "",
        "is_billable": False,
        "is_overtime": False,
        "start_time": "",
        "end_time": "",
        "vehicle_reimbursement_tier": "",
        "pto_type": pto.pto_type,
        "timesheet_id": str(ts.id),
        "timesheet_status": ts.status,
        "pay_period_start": pp.start_date.isoformat(),
        "pay_period_end": pp.end_date.isoformat(),
        "period_group": pp.period_group,
    }


async def _run_detail_report(
    db,
    employee_ids: list[UUID],
    start_date: date,
    end_date: date,
    timesheet_status: str | None,
    pay_period_status: str | None,
    include_pto: bool,
    format_param: str,
    filename_hint: str,
):
    """Core logic shared by employee-detail and my-time-detail."""

    # Validate date range
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be <= end_date",
        )
    if (end_date - start_date).days > _MAX_DATE_SPAN_DAYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Date range cannot exceed {_MAX_DATE_SPAN_DAYS} days",
        )

    statuses = _parse_statuses(timesheet_status)

    # --- Time entries ---
    te_query = (
        select(TimeEntry)
        .join(Timesheet, TimeEntry.timesheet_id == Timesheet.id)
        .join(PayPeriod, Timesheet.pay_period_id == PayPeriod.id)
        .where(Timesheet.employee_id.in_(employee_ids))
        .where(TimeEntry.work_date >= start_date)
        .where(TimeEntry.work_date <= end_date)
        .options(
            selectinload(TimeEntry.client),
            selectinload(TimeEntry.location),
            selectinload(TimeEntry.job_code),
            selectinload(TimeEntry.service_type),
            selectinload(TimeEntry.timesheet).selectinload(Timesheet.employee),
            selectinload(TimeEntry.timesheet).selectinload(Timesheet.pay_period),
        )
    )
    if statuses:
        te_query = te_query.where(Timesheet.status.in_(statuses))
    if pay_period_status and pay_period_status.lower() != "all":
        te_query = te_query.where(PayPeriod.status == pay_period_status.lower())

    result = await db.execute(te_query)
    time_entries = result.unique().scalars().all()

    rows: list[dict] = []
    for entry in time_entries:
        ts = entry.timesheet
        rows.append(_build_entry_row(entry, ts, ts.employee, ts.pay_period))

    # --- PTO entries ---
    if include_pto:
        pto_query = (
            select(PTOEntry)
            .join(Timesheet, PTOEntry.timesheet_id == Timesheet.id)
            .join(PayPeriod, Timesheet.pay_period_id == PayPeriod.id)
            .where(Timesheet.employee_id.in_(employee_ids))
            .where(PTOEntry.pto_date >= start_date)
            .where(PTOEntry.pto_date <= end_date)
            .options(
                selectinload(PTOEntry.timesheet).selectinload(Timesheet.employee),
                selectinload(PTOEntry.timesheet).selectinload(Timesheet.pay_period),
            )
        )
        if statuses:
            pto_query = pto_query.where(Timesheet.status.in_(statuses))
        if pay_period_status and pay_period_status.lower() != "all":
            pto_query = pto_query.where(PayPeriod.status == pay_period_status.lower())

        pto_result = await db.execute(pto_query)
        pto_entries = pto_result.unique().scalars().all()

        for pto in pto_entries:
            ts = pto.timesheet
            rows.append(_build_pto_row(pto, ts, ts.employee, ts.pay_period))

    # Sort: employee_name, work_date, entry_kind (pto after work), then description as tiebreaker
    rows.sort(key=lambda r: (r["employee_name"], r["work_date"], r["entry_kind"], r["description"]))

    # Build summary
    summary: dict[str, dict] = {}
    for r in rows:
        eid = r["employee_id"]
        if eid not in summary:
            summary[eid] = {
                "employee_id": eid,
                "employee_name": r["employee_name"],
                "total_work_hours": 0.0,
                "total_pto_hours": 0.0,
                "total_hours": 0.0,
            }
        h = float(r["hours"])
        if r["entry_kind"] == "work":
            summary[eid]["total_work_hours"] += h
        else:
            summary[eid]["total_pto_hours"] += h
        summary[eid]["total_hours"] += h

    summary_list = sorted(summary.values(), key=lambda s: s["employee_name"])
    grand_total = {
        "total_work_hours": sum(s["total_work_hours"] for s in summary_list),
        "total_pto_hours": sum(s["total_pto_hours"] for s in summary_list),
        "total_hours": sum(s["total_hours"] for s in summary_list),
    }

    if format_param == "json":
        return {
            "report": "employee_detail",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "row_count": len(rows),
            "summary": summary_list,
            "grand_total": grand_total,
            "data": rows,
        }

    df = pd.DataFrame(rows) if rows else pd.DataFrame()

    if format_param == "csv":
        output = BytesIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename_hint}.csv"},
        )

    if format_param == "excel":
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            if not df.empty:
                df.to_excel(writer, sheet_name="Detail", index=False)
            else:
                pd.DataFrame().to_excel(writer, sheet_name="Detail", index=False)
            # Summary sheet
            summary_df = pd.DataFrame(summary_list) if summary_list else pd.DataFrame()
            summary_df.to_excel(writer, sheet_name="Summary", index=False)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename_hint}.xlsx"},
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid format. Use json, csv, or excel.",
    )


@router.get("/employee-detail")
async def employee_detail_report(
    db: DB,
    current_user: CurrentManager,
    start_date: date,
    end_date: date,
    employee_id: UUID | None = None,
    employee_ids: str | None = None,
    timesheet_status: str | None = None,
    pay_period_status: str | None = None,
    include_pto: bool = True,
    format: str = "json",
):
    """
    Line-level detail report for one or many employees (manager/admin only).

    Employee selection: provide `employee_id` (single UUID) or `employee_ids`
    (comma-separated UUIDs). Exactly one must be provided.

    Filters:
        timesheet_status: comma-separated: draft,submitted,approved,rejected, or 'all' (default: all)
        pay_period_status: open, closed, or all (default: all)
        include_pto: include PTO rows (default: true)
        format: json, csv, excel
    """
    # Parse employee selection
    if employee_id and employee_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide employee_id or employee_ids, not both",
        )
    if not employee_id and not employee_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide employee_id (single) or employee_ids (comma-separated UUIDs)",
        )

    if employee_id:
        ids = [employee_id]
    else:
        try:
            ids = [UUID(s.strip()) for s in employee_ids.split(",") if s.strip()]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="employee_ids must be comma-separated valid UUIDs",
            )

    if not ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one employee ID is required",
        )
    if len(ids) > _MAX_EMPLOYEES_PER_REQUEST:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {_MAX_EMPLOYEES_PER_REQUEST} employees per request",
        )

    filename = f"employee_detail_{start_date}_{end_date}"
    return await _run_detail_report(
        db, ids, start_date, end_date,
        timesheet_status, pay_period_status,
        include_pto, format, filename,
    )


@router.get("/my-time-detail")
async def my_time_detail_report(
    db: DB,
    current_user: CurrentUser,
    start_date: date,
    end_date: date,
    timesheet_status: str | None = None,
    pay_period_status: str | None = None,
    include_pto: bool = True,
    format: str = "json",
):
    """
    Self-service line-level detail report for the current user's own entries.

    Any authenticated employee can download their own time and PTO entries.
    No employee_id parameter — always scoped to the logged-in user.

    Filters:
        timesheet_status: comma-separated: draft,submitted,approved,rejected, or 'all' (default: all)
        pay_period_status: open, closed, or all (default: all)
        include_pto: include PTO rows (default: true)
        format: json, csv, excel
    """
    filename = f"my_time_{current_user.first_name}_{current_user.last_name}_{start_date}_{end_date}"
    return await _run_detail_report(
        db, [current_user.id], start_date, end_date,
        timesheet_status, pay_period_status,
        include_pto, format, filename,
    )
