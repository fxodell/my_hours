from datetime import date, datetime, timedelta, timezone
from uuid import UUID
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from app.models.timesheet import Timesheet
from app.models.billing_week import BillingWeek
from app.models.time_entry import TimeEntry
from app.models.pto_entry import PTOEntry
from app.models.pay_period import PayPeriod
from app.models.employee import Employee
from app.schemas.timesheet import TimesheetCreate, TimesheetReject, TimesheetResponse
from app.schemas.time_entry import TimeEntryCreate, TimeEntryUpdate, TimeEntryResponse
from app.schemas.pto_entry import PTOEntryCreate, PTOEntryUpdate, PTOEntryResponse
from app.schemas.billing_week import BillingWeekResponse
from app.api.deps import DB, CurrentUser, CurrentManager, resolve_company_id
from app.services.email import email_service

router = APIRouter(prefix="/timesheets", tags=["timesheets"])


@router.get("", response_model=list[TimesheetResponse])
async def list_timesheets(
    db: DB,
    current_user: CurrentUser,
    pay_period_id: UUID | None = None,
    employee_id: UUID | None = None,
    status_filter: str | None = None,
    company_id: UUID | None = None,
) -> list[dict]:
    # Only list timesheets that have a valid pay period and employee (exclude orphans)
    cid = resolve_company_id(current_user, company_id)
    query = (
        select(Timesheet)
        .join(PayPeriod, Timesheet.pay_period_id == PayPeriod.id)
        .join(Employee, Timesheet.employee_id == Employee.id)
        .where(Timesheet.company_id == cid)
        .options(selectinload(Timesheet.employee), selectinload(Timesheet.pay_period))
    )

    # Non-managers can only see their own timesheets
    if not current_user.is_manager and not current_user.is_admin:
        query = query.where(Timesheet.employee_id == current_user.id)
    elif employee_id:
        query = query.where(Timesheet.employee_id == employee_id)

    if pay_period_id:
        query = query.where(Timesheet.pay_period_id == pay_period_id)

    if status_filter:
        query = query.where(Timesheet.status == status_filter)

    query = query.order_by(
        PayPeriod.start_date.desc(),
        Employee.last_name,
        Employee.first_name,
    )

    result = await db.execute(query)
    timesheets = list(result.unique().scalars().all())

    return [
        {
            **TimesheetResponse.model_validate(ts, from_attributes=True).model_dump(),
            "employee_name": ts.employee.full_name if ts.employee else None,
        }
        for ts in timesheets
    ]


@router.get("/current", response_model=TimesheetResponse)
async def get_current_timesheet(
    db: DB,
    current_user: CurrentUser,
) -> Timesheet:
    """Get or create the current pay period's timesheet for the logged-in user."""
    from datetime import date as date_type
    today = date_type.today()

    # Find the open pay period that contains today's date for the employee's group
    result = await db.execute(
        select(PayPeriod)
        .where(PayPeriod.company_id == current_user.company_id)
        .where(PayPeriod.status == "open")
        .where(PayPeriod.period_group == current_user.pay_period_group)
        .where(PayPeriod.start_date <= today)
        .where(PayPeriod.end_date >= today)
        .limit(1)
    )
    pay_period = result.scalar_one_or_none()

    # Fallback: nearest upcoming open pay period for the employee's group
    if not pay_period:
        result = await db.execute(
            select(PayPeriod)
            .where(PayPeriod.company_id == current_user.company_id)
            .where(PayPeriod.status == "open")
            .where(PayPeriod.period_group == current_user.pay_period_group)
            .where(PayPeriod.start_date >= today)
            .order_by(PayPeriod.start_date.asc())
            .limit(1)
        )
        pay_period = result.scalar_one_or_none()

    if not pay_period:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No open pay period found",
        )

    # Check if timesheet exists
    result = await db.execute(
        select(Timesheet)
        .where(Timesheet.employee_id == current_user.id)
        .where(Timesheet.pay_period_id == pay_period.id)
    )
    timesheet = result.scalar_one_or_none()

    if not timesheet:
        # Create new timesheet
        timesheet = Timesheet(
            company_id=current_user.company_id,
            employee_id=current_user.id,
            pay_period_id=pay_period.id,
            status="draft",
        )
        db.add(timesheet)
        await db.commit()
        await db.refresh(timesheet)

    await _ensure_billing_weeks(db, timesheet, pay_period)
    return timesheet


GRACE_PERIOD_DAYS = 7


def _monday_of_week(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _get_two_monday_sunday_weeks(start_date: date) -> list[tuple[date, date]]:
    first_monday = _monday_of_week(start_date)
    first_sunday = first_monday + timedelta(days=6)
    second_monday = first_monday + timedelta(days=7)
    second_sunday = second_monday + timedelta(days=6)
    return [
        (first_monday, first_sunday),
        (second_monday, second_sunday),
    ]


async def _ensure_billing_weeks(db: DB, timesheet: Timesheet, pay_period: PayPeriod) -> None:
    existing_result = await db.execute(
        select(BillingWeek)
        .where(BillingWeek.timesheet_id == timesheet.id)
        .order_by(BillingWeek.week_start_date.asc())
    )
    existing = list(existing_result.scalars().all())
    if existing:
        return

    for week_start, week_end in _get_two_monday_sunday_weeks(pay_period.start_date):
        db.add(
            BillingWeek(
                timesheet_id=timesheet.id,
                week_start_date=week_start,
                week_end_date=week_end,
                status="open",
            )
        )
    await db.commit()


async def _ensure_billing_weeks_for_timesheet_id(db: DB, timesheet_id: UUID) -> None:
    result = await db.execute(
        select(Timesheet, PayPeriod)
        .join(PayPeriod, Timesheet.pay_period_id == PayPeriod.id)
        .where(Timesheet.id == timesheet_id)
    )
    row = result.one_or_none()
    if not row:
        return
    timesheet, pay_period = row
    await _ensure_billing_weeks(db, timesheet, pay_period)


async def _is_date_locked_for_billing_week(db: DB, timesheet_id: UUID, target_date: date) -> bool:
    await _ensure_billing_weeks_for_timesheet_id(db, timesheet_id)
    result = await db.execute(
        select(BillingWeek)
        .where(BillingWeek.timesheet_id == timesheet_id)
        .where(BillingWeek.week_start_date <= target_date)
        .where(BillingWeek.week_end_date >= target_date)
        .limit(1)
    )
    billing_week = result.scalar_one_or_none()
    if not billing_week:
        return False
    return billing_week.status in ("approved", "billed")


@router.get("/for-period/{pay_period_id}", response_model=TimesheetResponse)
async def get_timesheet_for_period(
    pay_period_id: UUID,
    db: DB,
    current_user: CurrentUser,
) -> Timesheet:
    """Get or create a timesheet for a specific pay period.

    Allows open periods within 45 days, and closed periods still within
    the grace window (7 days after end_date) for late entries.
    Processed periods are always rejected.
    """
    from datetime import date as date_type, timedelta

    today = date_type.today()
    cutoff = today - timedelta(days=45)

    result = await db.execute(
        select(PayPeriod).where(PayPeriod.id == pay_period_id, PayPeriod.company_id == current_user.company_id)
    )
    pay_period = result.scalar_one_or_none()

    if not pay_period:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pay period not found",
        )

    # Prevent employees from creating timesheets in the wrong pay period group
    if pay_period.period_group != current_user.pay_period_group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pay period does not match your pay period group",
        )

    if pay_period.status == "processed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pay period has been processed and is locked",
        )

    if pay_period.status == "closed":
        grace_cutoff = today - timedelta(days=GRACE_PERIOD_DAYS)
        if pay_period.end_date < grace_cutoff:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pay period is closed and past the grace period for late entries",
            )

    if pay_period.end_date < cutoff:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pay period is too far in the past",
        )

    # Get or create timesheet
    result = await db.execute(
        select(Timesheet)
        .where(Timesheet.employee_id == current_user.id)
        .where(Timesheet.pay_period_id == pay_period.id)
    )
    timesheet = result.scalar_one_or_none()

    if not timesheet:
        timesheet = Timesheet(
            company_id=current_user.company_id,
            employee_id=current_user.id,
            pay_period_id=pay_period.id,
            status="draft",
        )
        db.add(timesheet)
        await db.commit()
        await db.refresh(timesheet)

    await _ensure_billing_weeks(db, timesheet, pay_period)
    return timesheet


@router.get("/{timesheet_id}", response_model=TimesheetResponse)
async def get_timesheet(
    timesheet_id: UUID,
    db: DB,
    current_user: CurrentUser,
) -> Timesheet:
    result = await db.execute(
        select(Timesheet)
        .where(Timesheet.id == timesheet_id)
        .where(Timesheet.company_id == current_user.company_id)
        .options(
            selectinload(Timesheet.time_entries),
            selectinload(Timesheet.pto_entries),
        )
    )
    timesheet = result.scalar_one_or_none()

    if not timesheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found",
        )

    # Check permissions
    if (
        timesheet.employee_id != current_user.id
        and not current_user.is_manager
        and not current_user.is_admin
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this timesheet",
        )

    return timesheet


@router.post("", response_model=TimesheetResponse, status_code=status.HTTP_201_CREATED)
async def create_timesheet(
    timesheet_data: TimesheetCreate,
    db: DB,
    current_user: CurrentUser,
) -> Timesheet:
    # Users can only create timesheets for themselves unless admin
    if timesheet_data.employee_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create timesheet for another user",
        )

    # Validate pay period belongs to the employee's group and company
    target_employee_id = timesheet_data.employee_id
    result = await db.execute(
        select(PayPeriod).where(PayPeriod.id == timesheet_data.pay_period_id, PayPeriod.company_id == current_user.company_id)
    )
    pay_period = result.scalar_one_or_none()
    if not pay_period:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pay period not found",
        )
    # For admin creating on behalf of another user, look up that employee's group
    if target_employee_id != current_user.id:
        from app.models.employee import Employee
        result = await db.execute(
            select(Employee).where(Employee.id == target_employee_id, Employee.company_id == current_user.company_id)
        )
        target_employee = result.scalar_one_or_none()
        if target_employee and pay_period.period_group != target_employee.pay_period_group:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pay period does not match the employee's pay period group",
            )
    elif pay_period.period_group != current_user.pay_period_group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pay period does not match your pay period group",
        )

    timesheet = Timesheet(company_id=current_user.company_id, **timesheet_data.model_dump())

    try:
        db.add(timesheet)
        await db.commit()
        await db.refresh(timesheet)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Timesheet already exists for this employee and pay period",
        )

    await _ensure_billing_weeks(db, timesheet, pay_period)
    return timesheet


@router.post("/{timesheet_id}/submit", response_model=TimesheetResponse)
async def submit_timesheet(
    timesheet_id: UUID,
    db: DB,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
) -> Timesheet:
    result = await db.execute(
        select(Timesheet, PayPeriod)
        .join(PayPeriod, Timesheet.pay_period_id == PayPeriod.id)
        .where(Timesheet.id == timesheet_id)
        .where(Timesheet.company_id == current_user.company_id)
    )
    row = result.one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found",
        )

    timesheet, pay_period = row

    if timesheet.employee_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only submit your own timesheet",
        )

    if timesheet.status not in ("draft", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit timesheet with status '{timesheet.status}'",
        )

    # Calculate total hours (work + PTO) for notifications
    hours_result = await db.execute(
        select(func.coalesce(func.sum(TimeEntry.hours), 0))
        .where(TimeEntry.timesheet_id == timesheet_id)
    )
    pto_hours_result = await db.execute(
        select(func.coalesce(func.sum(PTOEntry.hours), 0))
        .where(PTOEntry.timesheet_id == timesheet_id)
    )
    total_hours = float(hours_result.scalar() or 0) + float(pto_hours_result.scalar() or 0)

    timesheet.status = "submitted"
    timesheet.submitted_at = datetime.now(timezone.utc)
    # Clear rejection metadata when submitting.
    timesheet.rejection_reason = None

    await db.commit()
    await db.refresh(timesheet)

    # Send notification to managers (in background)
    managers_result = await db.execute(
        select(Employee).where(Employee.company_id == current_user.company_id).where(Employee.is_manager == True).where(Employee.is_active == True)
    )
    managers = managers_result.scalars().all()

    pay_period_str = f"{pay_period.start_date} to {pay_period.end_date}"
    for manager in managers:
        background_tasks.add_task(
            email_service.send_timesheet_submitted,
            current_user.email,
            current_user.full_name,
            manager.email,
            manager.full_name,
            pay_period_str,
            total_hours,
        )

    return timesheet


@router.post("/{timesheet_id}/approve", response_model=TimesheetResponse)
async def approve_timesheet(
    timesheet_id: UUID,
    db: DB,
    current_user: CurrentManager,
    background_tasks: BackgroundTasks,
) -> Timesheet:
    result = await db.execute(
        select(Timesheet, PayPeriod, Employee)
        .join(PayPeriod, Timesheet.pay_period_id == PayPeriod.id)
        .join(Employee, Timesheet.employee_id == Employee.id)
        .where(Timesheet.id == timesheet_id)
        .where(Timesheet.company_id == current_user.company_id)
    )
    row = result.one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found",
        )

    timesheet, pay_period, employee = row

    if timesheet.status != "submitted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve timesheet with status '{timesheet.status}'",
        )

    timesheet.status = "approved"
    timesheet.approved_at = datetime.now(timezone.utc)
    timesheet.approved_by = current_user.id
    timesheet.rejection_reason = None

    await db.commit()
    await db.refresh(timesheet)

    # Send notification to employee (in background)
    pay_period_str = f"{pay_period.start_date} to {pay_period.end_date}"
    background_tasks.add_task(
        email_service.send_timesheet_approved,
        employee.email,
        employee.full_name,
        pay_period_str,
        current_user.full_name,
    )

    return timesheet


@router.post("/{timesheet_id}/reject", response_model=TimesheetResponse)
async def reject_timesheet(
    timesheet_id: UUID,
    body: TimesheetReject,
    db: DB,
    current_user: CurrentManager,
    background_tasks: BackgroundTasks,
) -> Timesheet:
    result = await db.execute(
        select(Timesheet, PayPeriod, Employee)
        .join(PayPeriod, Timesheet.pay_period_id == PayPeriod.id)
        .join(Employee, Timesheet.employee_id == Employee.id)
        .where(Timesheet.id == timesheet_id)
        .where(Timesheet.company_id == current_user.company_id)
    )
    row = result.one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found",
        )

    timesheet, pay_period, employee = row

    if timesheet.status != "submitted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject timesheet with status '{timesheet.status}'",
        )

    timesheet.status = "rejected"
    timesheet.rejection_reason = body.rejection_reason

    await db.commit()
    await db.refresh(timesheet)

    # Send notification to employee (in background)
    pay_period_str = f"{pay_period.start_date} to {pay_period.end_date}"
    background_tasks.add_task(
        email_service.send_timesheet_rejected,
        employee.email,
        employee.full_name,
        pay_period_str,
        current_user.full_name,
        body.rejection_reason,
    )

    return timesheet


@router.get("/{timesheet_id}/billing-weeks", response_model=list[BillingWeekResponse])
async def list_billing_weeks(
    timesheet_id: UUID,
    db: DB,
    current_user: CurrentUser,
) -> list[BillingWeek]:
    result = await db.execute(
        select(Timesheet, PayPeriod)
        .join(PayPeriod, Timesheet.pay_period_id == PayPeriod.id)
        .where(Timesheet.id == timesheet_id)
        .where(Timesheet.company_id == current_user.company_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found",
        )
    timesheet, pay_period = row

    if (
        timesheet.employee_id != current_user.id
        and not current_user.is_manager
        and not current_user.is_admin
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this timesheet",
        )

    await _ensure_billing_weeks(db, timesheet, pay_period)
    result = await db.execute(
        select(BillingWeek)
        .where(BillingWeek.timesheet_id == timesheet_id)
        .order_by(BillingWeek.week_start_date.asc())
    )
    return list(result.scalars().all())


async def _update_billing_week_status(
    timesheet_id: UUID,
    week_id: UUID,
    db: DB,
    current_user: CurrentManager,
    target_status: str,
) -> BillingWeek:
    result = await db.execute(select(Timesheet).where(Timesheet.id == timesheet_id, Timesheet.company_id == current_user.company_id))
    timesheet = result.scalar_one_or_none()
    if not timesheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found",
        )

    result = await db.execute(
        select(BillingWeek)
        .where(BillingWeek.id == week_id)
        .where(BillingWeek.timesheet_id == timesheet_id)
    )
    billing_week = result.scalar_one_or_none()
    if not billing_week:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Billing week not found",
        )

    now = datetime.now(timezone.utc)
    if target_status == "submitted":
        if billing_week.status not in ("open", "reopened"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot submit billing week with status '{billing_week.status}'",
            )
        billing_week.status = "submitted"
        billing_week.submitted_at = now
    elif target_status == "approved":
        if billing_week.status != "submitted":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve billing week with status '{billing_week.status}'",
            )
        billing_week.status = "approved"
        billing_week.approved_at = now
        billing_week.approved_by = current_user.id
    elif target_status == "reopened":
        if billing_week.status not in ("submitted", "approved", "billed"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reopen billing week with status '{billing_week.status}'",
            )
        billing_week.status = "reopened"
        billing_week.approved_at = None
        billing_week.approved_by = None
        billing_week.billed_at = None
    elif target_status == "billed":
        if billing_week.status != "approved":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot mark billed for billing week with status '{billing_week.status}'",
            )
        billing_week.status = "billed"
        billing_week.billed_at = now
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported billing week status transition",
        )

    await db.commit()
    await db.refresh(billing_week)
    return billing_week


@router.post("/{timesheet_id}/billing-weeks/{week_id}/submit", response_model=BillingWeekResponse)
async def submit_billing_week(
    timesheet_id: UUID,
    week_id: UUID,
    db: DB,
    current_user: CurrentManager,
) -> BillingWeek:
    return await _update_billing_week_status(timesheet_id, week_id, db, current_user, "submitted")


@router.post("/{timesheet_id}/billing-weeks/{week_id}/approve", response_model=BillingWeekResponse)
async def approve_billing_week(
    timesheet_id: UUID,
    week_id: UUID,
    db: DB,
    current_user: CurrentManager,
) -> BillingWeek:
    return await _update_billing_week_status(timesheet_id, week_id, db, current_user, "approved")


@router.post("/{timesheet_id}/billing-weeks/{week_id}/reopen", response_model=BillingWeekResponse)
async def reopen_billing_week(
    timesheet_id: UUID,
    week_id: UUID,
    db: DB,
    current_user: CurrentManager,
) -> BillingWeek:
    return await _update_billing_week_status(timesheet_id, week_id, db, current_user, "reopened")


@router.post("/{timesheet_id}/billing-weeks/{week_id}/mark-billed", response_model=BillingWeekResponse)
async def mark_billed_billing_week(
    timesheet_id: UUID,
    week_id: UUID,
    db: DB,
    current_user: CurrentManager,
) -> BillingWeek:
    return await _update_billing_week_status(timesheet_id, week_id, db, current_user, "billed")


# Time entries within a timesheet
@router.get("/{timesheet_id}/entries", response_model=list[TimeEntryResponse])
async def list_time_entries(
    timesheet_id: UUID,
    db: DB,
    current_user: CurrentUser,
) -> list[TimeEntry]:
    # Verify access to timesheet and get pay period for date filtering
    result = await db.execute(
        select(Timesheet, PayPeriod)
        .join(PayPeriod, Timesheet.pay_period_id == PayPeriod.id)
        .where(Timesheet.id == timesheet_id)
        .where(Timesheet.company_id == current_user.company_id)
    )
    row = result.one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found",
        )

    timesheet, pay_period = row

    if (
        timesheet.employee_id != current_user.id
        and not current_user.is_manager
        and not current_user.is_admin
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this timesheet",
        )

    # Only return entries whose work_date falls within this timesheet's pay period
    result = await db.execute(
        select(TimeEntry)
        .where(TimeEntry.timesheet_id == timesheet_id)
        .where(TimeEntry.work_date >= pay_period.start_date)
        .where(TimeEntry.work_date <= pay_period.end_date)
        .order_by(TimeEntry.work_date, TimeEntry.created_at)
    )
    return list(result.scalars().all())


@router.post(
    "/{timesheet_id}/entries",
    response_model=TimeEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_time_entry(
    timesheet_id: UUID,
    entry_data: TimeEntryCreate,
    db: DB,
    current_user: CurrentUser,
) -> TimeEntry:
    # Verify timesheet access and status
    result = await db.execute(
        select(Timesheet, PayPeriod)
        .join(PayPeriod, Timesheet.pay_period_id == PayPeriod.id)
        .where(Timesheet.id == timesheet_id)
        .where(Timesheet.company_id == current_user.company_id)
    )
    row = result.one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found",
        )

    timesheet, pay_period = row

    if timesheet.employee_id != current_user.id and not current_user.is_manager and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only add entries to your own timesheet",
        )

    if timesheet.status not in ("draft", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot add entries to timesheet with status '{timesheet.status}'",
        )

    # Validate work_date is within pay period
    if entry_data.work_date < pay_period.start_date or entry_data.work_date > pay_period.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Work date must be within pay period ({pay_period.start_date} to {pay_period.end_date})",
        )
    if await _is_date_locked_for_billing_week(db, timesheet_id, entry_data.work_date):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify entry in a billing week that is approved or billed",
        )

    entry = TimeEntry(timesheet_id=timesheet_id, **entry_data.model_dump())
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    # Reset timesheet to draft if it was rejected
    if timesheet.status == "rejected":
        timesheet.status = "draft"
        timesheet.rejection_reason = None
        await db.commit()

    return entry


@router.patch("/{timesheet_id}/entries/{entry_id}", response_model=TimeEntryResponse)
async def update_time_entry(
    timesheet_id: UUID,
    entry_id: UUID,
    entry_data: TimeEntryUpdate,
    db: DB,
    current_user: CurrentUser,
) -> TimeEntry:
    # Verify timesheet access and status
    result = await db.execute(
        select(Timesheet, PayPeriod)
        .join(PayPeriod, Timesheet.pay_period_id == PayPeriod.id)
        .where(Timesheet.id == timesheet_id)
        .where(Timesheet.company_id == current_user.company_id)
    )
    row = result.one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found",
        )

    timesheet, pay_period = row

    if timesheet.employee_id != current_user.id and not current_user.is_manager and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only edit entries in your own timesheet",
        )

    if timesheet.status not in ("draft", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot edit entries in timesheet with status '{timesheet.status}'",
        )

    # Keep workflow consistent with create endpoints:
    # when editing a rejected timesheet, move it back to draft.
    if timesheet.status == "rejected":
        timesheet.status = "draft"
        timesheet.rejection_reason = None

    result = await db.execute(
        select(TimeEntry)
        .where(TimeEntry.id == entry_id)
        .where(TimeEntry.timesheet_id == timesheet_id)
    )
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Time entry not found",
        )

    target_work_date = entry_data.work_date if entry_data.work_date is not None else entry.work_date
    if target_work_date < pay_period.start_date or target_work_date > pay_period.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Work date must be within pay period ({pay_period.start_date} to {pay_period.end_date})",
        )
    if await _is_date_locked_for_billing_week(db, timesheet_id, target_work_date):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify entry in a billing week that is approved or billed",
        )

    update_data = entry_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(entry, field, value)

    await db.commit()
    await db.refresh(entry)

    return entry


@router.delete(
    "/{timesheet_id}/entries/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_time_entry(
    timesheet_id: UUID,
    entry_id: UUID,
    db: DB,
    current_user: CurrentUser,
) -> None:
    # Verify timesheet access and status
    result = await db.execute(select(Timesheet).where(Timesheet.id == timesheet_id, Timesheet.company_id == current_user.company_id))
    timesheet = result.scalar_one_or_none()

    if not timesheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found",
        )

    if timesheet.employee_id != current_user.id and not current_user.is_manager and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only delete entries from your own timesheet",
        )

    if timesheet.status not in ("draft", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot delete entries from timesheet with status '{timesheet.status}'",
        )

    # Keep workflow consistent with create endpoints:
    # when deleting from a rejected timesheet, move it back to draft.
    if timesheet.status == "rejected":
        timesheet.status = "draft"
        timesheet.rejection_reason = None

    result = await db.execute(
        select(TimeEntry)
        .where(TimeEntry.id == entry_id)
        .where(TimeEntry.timesheet_id == timesheet_id)
    )
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Time entry not found",
        )
    if await _is_date_locked_for_billing_week(db, timesheet_id, entry.work_date):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify entry in a billing week that is approved or billed",
        )

    await db.delete(entry)
    await db.commit()


# PTO entries
@router.get("/{timesheet_id}/pto", response_model=list[PTOEntryResponse])
async def list_pto_entries(
    timesheet_id: UUID,
    db: DB,
    current_user: CurrentUser,
) -> list[PTOEntry]:
    # Verify access to timesheet and get pay period for date filtering
    result = await db.execute(
        select(Timesheet, PayPeriod)
        .join(PayPeriod, Timesheet.pay_period_id == PayPeriod.id)
        .where(Timesheet.id == timesheet_id)
        .where(Timesheet.company_id == current_user.company_id)
    )
    row = result.one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found",
        )

    timesheet, pay_period = row

    if (
        timesheet.employee_id != current_user.id
        and not current_user.is_manager
        and not current_user.is_admin
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this timesheet",
        )

    # Only return entries whose pto_date falls within this timesheet's pay period
    result = await db.execute(
        select(PTOEntry)
        .where(PTOEntry.timesheet_id == timesheet_id)
        .where(PTOEntry.pto_date >= pay_period.start_date)
        .where(PTOEntry.pto_date <= pay_period.end_date)
        .order_by(PTOEntry.pto_date)
    )
    return list(result.scalars().all())


@router.post(
    "/{timesheet_id}/pto",
    response_model=PTOEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_pto_entry(
    timesheet_id: UUID,
    entry_data: PTOEntryCreate,
    db: DB,
    current_user: CurrentUser,
) -> PTOEntry:
    result = await db.execute(
        select(Timesheet, PayPeriod)
        .join(PayPeriod, Timesheet.pay_period_id == PayPeriod.id)
        .where(Timesheet.id == timesheet_id)
        .where(Timesheet.company_id == current_user.company_id)
    )
    row = result.one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found",
        )

    timesheet, pay_period = row

    if timesheet.employee_id != current_user.id and not current_user.is_manager and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only add PTO to your own timesheet",
        )

    if timesheet.status not in ("draft", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot add PTO to timesheet with status '{timesheet.status}'",
        )

    # Validate pto_date is within pay period
    if entry_data.pto_date < pay_period.start_date or entry_data.pto_date > pay_period.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"PTO date must be within pay period ({pay_period.start_date} to {pay_period.end_date})",
        )
    if await _is_date_locked_for_billing_week(db, timesheet_id, entry_data.pto_date):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify PTO in a billing week that is approved or billed",
        )

    entry = PTOEntry(timesheet_id=timesheet_id, **entry_data.model_dump())
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    # Reset timesheet to draft if it was rejected
    if timesheet.status == "rejected":
        timesheet.status = "draft"
        timesheet.rejection_reason = None
        await db.commit()

    return entry


@router.patch("/{timesheet_id}/pto/{entry_id}", response_model=PTOEntryResponse)
async def update_pto_entry(
    timesheet_id: UUID,
    entry_id: UUID,
    entry_data: PTOEntryUpdate,
    db: DB,
    current_user: CurrentUser,
) -> PTOEntry:
    result = await db.execute(
        select(Timesheet, PayPeriod)
        .join(PayPeriod, Timesheet.pay_period_id == PayPeriod.id)
        .where(Timesheet.id == timesheet_id)
        .where(Timesheet.company_id == current_user.company_id)
    )
    row = result.one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found",
        )

    timesheet, pay_period = row

    if timesheet.employee_id != current_user.id and not current_user.is_manager and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only edit PTO in your own timesheet",
        )

    if timesheet.status not in ("draft", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot edit PTO in timesheet with status '{timesheet.status}'",
        )

    # Keep workflow consistent with create endpoints:
    # when editing a rejected timesheet, move it back to draft.
    if timesheet.status == "rejected":
        timesheet.status = "draft"
        timesheet.rejection_reason = None

    result = await db.execute(
        select(PTOEntry)
        .where(PTOEntry.id == entry_id)
        .where(PTOEntry.timesheet_id == timesheet_id)
    )
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PTO entry not found",
        )

    target_pto_date = entry_data.pto_date if entry_data.pto_date is not None else entry.pto_date
    if target_pto_date < pay_period.start_date or target_pto_date > pay_period.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"PTO date must be within pay period ({pay_period.start_date} to {pay_period.end_date})",
        )
    if await _is_date_locked_for_billing_week(db, timesheet_id, target_pto_date):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify PTO in a billing week that is approved or billed",
        )

    update_data = entry_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(entry, field, value)

    await db.commit()
    await db.refresh(entry)

    return entry


@router.delete(
    "/{timesheet_id}/pto/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_pto_entry(
    timesheet_id: UUID,
    entry_id: UUID,
    db: DB,
    current_user: CurrentUser,
) -> None:
    result = await db.execute(select(Timesheet).where(Timesheet.id == timesheet_id, Timesheet.company_id == current_user.company_id))
    timesheet = result.scalar_one_or_none()

    if not timesheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found",
        )

    if timesheet.employee_id != current_user.id and not current_user.is_manager and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only delete PTO from your own timesheet",
        )

    if timesheet.status not in ("draft", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot delete PTO from timesheet with status '{timesheet.status}'",
        )

    # Keep workflow consistent with create endpoints:
    # when deleting from a rejected timesheet, move it back to draft.
    if timesheet.status == "rejected":
        timesheet.status = "draft"
        timesheet.rejection_reason = None

    result = await db.execute(
        select(PTOEntry)
        .where(PTOEntry.id == entry_id)
        .where(PTOEntry.timesheet_id == timesheet_id)
    )
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PTO entry not found",
        )
    if await _is_date_locked_for_billing_week(db, timesheet_id, entry.pto_date):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify PTO in a billing week that is approved or billed",
        )

    await db.delete(entry)
    await db.commit()


@router.delete(
    "/{timesheet_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_timesheet(
    timesheet_id: UUID,
    db: DB,
    current_user: CurrentManager,
) -> None:
    """Delete a timesheet (manager/admin only)."""
    result = await db.execute(select(Timesheet).where(Timesheet.id == timesheet_id, Timesheet.company_id == current_user.company_id))
    timesheet = result.scalar_one_or_none()

    if not timesheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found",
        )

    await db.delete(timesheet)
    await db.commit()


@router.post("/{timesheet_id}/reopen", response_model=TimesheetResponse)
async def reopen_timesheet(
    timesheet_id: UUID,
    db: DB,
    current_user: CurrentManager,
) -> Timesheet:
    """Reopen an approved or submitted timesheet back to draft (manager/admin only)."""
    result = await db.execute(select(Timesheet).where(Timesheet.id == timesheet_id, Timesheet.company_id == current_user.company_id))
    timesheet = result.scalar_one_or_none()

    if not timesheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found",
        )

    if timesheet.status not in ("submitted", "approved"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reopen timesheet with status '{timesheet.status}'",
        )

    timesheet.status = "draft"
    timesheet.submitted_at = None
    timesheet.approved_at = None
    timesheet.approved_by = None
    timesheet.rejection_reason = None

    await db.commit()
    await db.refresh(timesheet)

    return timesheet
