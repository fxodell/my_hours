import asyncio
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from app.models.timesheet import Timesheet
from app.models.time_entry import TimeEntry
from app.models.pto_entry import PTOEntry
from app.models.pay_period import PayPeriod
from app.models.employee import Employee
from app.schemas.timesheet import TimesheetCreate, TimesheetResponse
from app.schemas.time_entry import TimeEntryCreate, TimeEntryUpdate, TimeEntryResponse
from app.schemas.pto_entry import PTOEntryCreate, PTOEntryUpdate, PTOEntryResponse
from app.api.deps import DB, CurrentUser, CurrentManager
from app.services.email import email_service

router = APIRouter(prefix="/timesheets", tags=["timesheets"])


@router.get("", response_model=list[TimesheetResponse])
async def list_timesheets(
    db: DB,
    current_user: CurrentUser,
    pay_period_id: UUID | None = None,
    employee_id: UUID | None = None,
    status_filter: str | None = None,
) -> list[Timesheet]:
    query = select(Timesheet)

    # Non-managers can only see their own timesheets
    if not current_user.is_manager and not current_user.is_admin:
        query = query.where(Timesheet.employee_id == current_user.id)
    elif employee_id:
        query = query.where(Timesheet.employee_id == employee_id)

    if pay_period_id:
        query = query.where(Timesheet.pay_period_id == pay_period_id)

    if status_filter:
        query = query.where(Timesheet.status == status_filter)

    query = query.order_by(Timesheet.created_at.desc())

    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/current", response_model=TimesheetResponse)
async def get_current_timesheet(
    db: DB,
    current_user: CurrentUser,
) -> Timesheet:
    """Get or create the current pay period's timesheet for the logged-in user."""
    from datetime import date as date_type
    today = date_type.today()

    # Find the open pay period that contains today's date
    result = await db.execute(
        select(PayPeriod)
        .where(PayPeriod.period_group == current_user.pay_period_group)
        .where(PayPeriod.status == "open")
        .where(PayPeriod.start_date <= today)
        .where(PayPeriod.end_date >= today)
        .limit(1)
    )
    pay_period = result.scalar_one_or_none()

    # Fallback: nearest upcoming open pay period
    if not pay_period:
        result = await db.execute(
            select(PayPeriod)
            .where(PayPeriod.period_group == current_user.pay_period_group)
            .where(PayPeriod.status == "open")
            .where(PayPeriod.start_date >= today)
            .order_by(PayPeriod.start_date.asc())
            .limit(1)
        )
        pay_period = result.scalar_one_or_none()

    if not pay_period:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No open pay period found for your pay period group",
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
            employee_id=current_user.id,
            pay_period_id=pay_period.id,
            status="draft",
        )
        db.add(timesheet)
        await db.commit()
        await db.refresh(timesheet)

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

    timesheet = Timesheet(**timesheet_data.model_dump())

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

    if timesheet.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit timesheet with status '{timesheet.status}'",
        )

    # Calculate total hours
    hours_result = await db.execute(
        select(func.coalesce(func.sum(TimeEntry.hours), 0))
        .where(TimeEntry.timesheet_id == timesheet_id)
    )
    total_hours = float(hours_result.scalar())

    timesheet.status = "submitted"
    timesheet.submitted_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(timesheet)

    # Send notification to managers (in background)
    managers_result = await db.execute(
        select(Employee).where(Employee.is_manager == True).where(Employee.is_active == True)
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
    rejection_reason: str,
    db: DB,
    current_user: CurrentManager,
    background_tasks: BackgroundTasks,
) -> Timesheet:
    result = await db.execute(
        select(Timesheet, PayPeriod, Employee)
        .join(PayPeriod, Timesheet.pay_period_id == PayPeriod.id)
        .join(Employee, Timesheet.employee_id == Employee.id)
        .where(Timesheet.id == timesheet_id)
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
    timesheet.rejection_reason = rejection_reason
    timesheet.approved_by = current_user.id

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
        rejection_reason,
    )

    return timesheet


# Time entries within a timesheet
@router.get("/{timesheet_id}/entries", response_model=list[TimeEntryResponse])
async def list_time_entries(
    timesheet_id: UUID,
    db: DB,
    current_user: CurrentUser,
) -> list[TimeEntry]:
    # First verify access to timesheet
    result = await db.execute(select(Timesheet).where(Timesheet.id == timesheet_id))
    timesheet = result.scalar_one_or_none()

    if not timesheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found",
        )

    if (
        timesheet.employee_id != current_user.id
        and not current_user.is_manager
        and not current_user.is_admin
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this timesheet",
        )

    result = await db.execute(
        select(TimeEntry)
        .where(TimeEntry.timesheet_id == timesheet_id)
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
            detail="Can only add entries to your own timesheet",
        )

    if timesheet.status not in ("draft", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot add entries to timesheet with status '{timesheet.status}'",
        )

    # Validate work_date is within pay period
    if entry_data.work_date < pay_period.start_date or entry_data.work_date > pay_period.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Work date must be within pay period ({pay_period.start_date} to {pay_period.end_date})",
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
            detail="Can only edit entries in your own timesheet",
        )

    if timesheet.status not in ("draft", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot edit entries in timesheet with status '{timesheet.status}'",
        )

    # Validate work_date if provided
    if entry_data.work_date is not None:
        if entry_data.work_date < pay_period.start_date or entry_data.work_date > pay_period.end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Work date must be within pay period ({pay_period.start_date} to {pay_period.end_date})",
            )

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
    result = await db.execute(select(Timesheet).where(Timesheet.id == timesheet_id))
    timesheet = result.scalar_one_or_none()

    if not timesheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found",
        )

    if timesheet.employee_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only delete entries from your own timesheet",
        )

    if timesheet.status not in ("draft", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete entries from timesheet with status '{timesheet.status}'",
        )

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

    await db.delete(entry)
    await db.commit()


# PTO entries
@router.get("/{timesheet_id}/pto", response_model=list[PTOEntryResponse])
async def list_pto_entries(
    timesheet_id: UUID,
    db: DB,
    current_user: CurrentUser,
) -> list[PTOEntry]:
    result = await db.execute(select(Timesheet).where(Timesheet.id == timesheet_id))
    timesheet = result.scalar_one_or_none()

    if not timesheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found",
        )

    if (
        timesheet.employee_id != current_user.id
        and not current_user.is_manager
        and not current_user.is_admin
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this timesheet",
        )

    result = await db.execute(
        select(PTOEntry)
        .where(PTOEntry.timesheet_id == timesheet_id)
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
    result = await db.execute(select(Timesheet).where(Timesheet.id == timesheet_id))
    timesheet = result.scalar_one_or_none()

    if not timesheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found",
        )

    if timesheet.employee_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only add PTO to your own timesheet",
        )

    if timesheet.status not in ("draft", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot add PTO to timesheet with status '{timesheet.status}'",
        )

    entry = PTOEntry(timesheet_id=timesheet_id, **entry_data.model_dump())
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    return entry


@router.patch("/{timesheet_id}/pto/{entry_id}", response_model=PTOEntryResponse)
async def update_pto_entry(
    timesheet_id: UUID,
    entry_id: UUID,
    entry_data: PTOEntryUpdate,
    db: DB,
    current_user: CurrentUser,
) -> PTOEntry:
    result = await db.execute(select(Timesheet).where(Timesheet.id == timesheet_id))
    timesheet = result.scalar_one_or_none()

    if not timesheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found",
        )

    if timesheet.employee_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only edit PTO in your own timesheet",
        )

    if timesheet.status not in ("draft", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot edit PTO in timesheet with status '{timesheet.status}'",
        )

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
    result = await db.execute(select(Timesheet).where(Timesheet.id == timesheet_id))
    timesheet = result.scalar_one_or_none()

    if not timesheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet not found",
        )

    if timesheet.employee_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only delete PTO from your own timesheet",
        )

    if timesheet.status not in ("draft", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete PTO from timesheet with status '{timesheet.status}'",
        )

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

    await db.delete(entry)
    await db.commit()
