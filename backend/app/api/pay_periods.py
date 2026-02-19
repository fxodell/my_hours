from datetime import date, timedelta
from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.pay_period import PayPeriod
from app.schemas.pay_period import PayPeriodCreate, PayPeriodUpdate, PayPeriodResponse
from app.api.deps import DB, CurrentUser, CurrentAdmin

router = APIRouter(prefix="/pay-periods", tags=["pay-periods"])


@router.get("", response_model=list[PayPeriodResponse])
async def list_pay_periods(
    db: DB,
    current_user: CurrentUser,
    period_group: str | None = None,
    status_filter: str | None = None,
    limit: int = 20,
) -> list[PayPeriod]:
    query = select(PayPeriod)

    if period_group:
        query = query.where(PayPeriod.period_group == period_group)

    if status_filter:
        query = query.where(PayPeriod.status == status_filter)

    query = query.order_by(PayPeriod.start_date.desc()).limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/current", response_model=PayPeriodResponse)
async def get_current_pay_period(
    db: DB,
    current_user: CurrentUser,
) -> PayPeriod:
    """Get the current open pay period for the logged-in user's pay period group."""
    today = date.today()

    # First try to find an open pay period that contains today's date
    result = await db.execute(
        select(PayPeriod)
        .where(PayPeriod.period_group == current_user.pay_period_group)
        .where(PayPeriod.status == "open")
        .where(PayPeriod.start_date <= today)
        .where(PayPeriod.end_date >= today)
        .limit(1)
    )
    pay_period = result.scalar_one_or_none()

    # Fallback: find the nearest upcoming open pay period
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
            detail="No open pay period found",
        )

    return pay_period


@router.get("/{pay_period_id}", response_model=PayPeriodResponse)
async def get_pay_period(
    pay_period_id: UUID,
    db: DB,
    current_user: CurrentUser,
) -> PayPeriod:
    result = await db.execute(select(PayPeriod).where(PayPeriod.id == pay_period_id))
    pay_period = result.scalar_one_or_none()

    if not pay_period:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pay period not found",
        )

    return pay_period


@router.post("", response_model=PayPeriodResponse, status_code=status.HTTP_201_CREATED)
async def create_pay_period(
    pay_period_data: PayPeriodCreate,
    db: DB,
    current_user: CurrentAdmin,
) -> PayPeriod:
    pay_period = PayPeriod(**pay_period_data.model_dump())

    try:
        db.add(pay_period)
        await db.commit()
        await db.refresh(pay_period)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Pay period already exists for this group and start date",
        )

    return pay_period


@router.post("/generate", response_model=list[PayPeriodResponse])
async def generate_pay_periods(
    db: DB,
    current_user: CurrentAdmin,
    start_date: date,
    weeks: int = 8,
) -> list[PayPeriod]:
    """
    Generate pay periods for both groups (A and B) starting from a date.
    Creates bi-weekly periods (14 days each), staggered by 1 week.
    """
    created_periods = []

    for group in ["A", "B"]:
        # Group B starts 1 week after Group A
        group_start = start_date if group == "A" else start_date + timedelta(days=7)

        for i in range(weeks // 2):  # bi-weekly, so half the weeks
            period_start = group_start + timedelta(days=14 * i)
            period_end = period_start + timedelta(days=13)

            # Check if period already exists
            result = await db.execute(
                select(PayPeriod)
                .where(PayPeriod.period_group == group)
                .where(PayPeriod.start_date == period_start)
            )
            existing = result.scalar_one_or_none()

            if not existing:
                pay_period = PayPeriod(
                    period_group=group,
                    start_date=period_start,
                    end_date=period_end,
                    status="open",
                )
                db.add(pay_period)
                created_periods.append(pay_period)

    await db.commit()

    for period in created_periods:
        await db.refresh(period)

    return created_periods


@router.patch("/{pay_period_id}", response_model=PayPeriodResponse)
async def update_pay_period(
    pay_period_id: UUID,
    pay_period_data: PayPeriodUpdate,
    db: DB,
    current_user: CurrentAdmin,
) -> PayPeriod:
    result = await db.execute(select(PayPeriod).where(PayPeriod.id == pay_period_id))
    pay_period = result.scalar_one_or_none()

    if not pay_period:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pay period not found",
        )

    update_data = pay_period_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(pay_period, field, value)

    await db.commit()
    await db.refresh(pay_period)

    return pay_period


@router.post("/{pay_period_id}/close", response_model=PayPeriodResponse)
async def close_pay_period(
    pay_period_id: UUID,
    db: DB,
    current_user: CurrentAdmin,
) -> PayPeriod:
    result = await db.execute(select(PayPeriod).where(PayPeriod.id == pay_period_id))
    pay_period = result.scalar_one_or_none()

    if not pay_period:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pay period not found",
        )

    if pay_period.status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pay period is already '{pay_period.status}'",
        )

    pay_period.status = "closed"
    await db.commit()
    await db.refresh(pay_period)

    return pay_period
