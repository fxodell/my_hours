from datetime import date
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
from app.api.deps import DB, CurrentManager

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

    result = await db.execute(query)
    timesheets = result.scalars().all()

    # Build report data
    report_data = []
    for ts in timesheets:
        if start_date and ts.pay_period.end_date < start_date:
            continue
        if end_date and ts.pay_period.start_date > end_date:
            continue

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
        report_data.append({
            "date": entry.work_date.isoformat(),
            "client": entry.client.name if entry.client else "Unassigned",
            "employee": entry.timesheet.employee.full_name,
            "service_type": entry.service_type.name if entry.service_type else "General",
            "hours": float(entry.hours),
            "work_mode": entry.work_mode,
            "description": entry.description or "",
            "bonus_eligible": entry.bonus_eligible,
        })

    if format == "json":
        # Also provide summary by client
        summary = {}
        for row in report_data:
            client = row["client"]
            if client not in summary:
                summary[client] = {"hours": 0, "bonus_hours": 0}
            summary[client]["hours"] += row["hours"]
            if row["bonus_eligible"]:
                summary[client]["bonus_hours"] += row["hours"]

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
                bonus = sum(r["hours"] for r in client_rows if r["bonus_eligible"])
                summary_data.append({
                    "Client": client,
                    "Total Hours": total,
                    "Bonus Hours": bonus,
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

            if entry.bonus_eligible:
                bonus_hours += hours

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

        # Bonus calculation ($5/billable hour for Data clients)
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
