from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.location import Location
from app.models.job_code import JobCode
from app.schemas.location import LocationCreate, LocationUpdate, LocationResponse
from app.schemas.job_code import JobCodeCreate, JobCodeUpdate, JobCodeResponse
from app.api.deps import DB, CurrentUser, CurrentAdmin

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("", response_model=list[LocationResponse])
async def list_locations(
    db: DB,
    current_user: CurrentUser,
    client_id: UUID | None = None,
    active_only: bool = True,
) -> list[Location]:
    query = select(Location)

    if client_id:
        query = query.where(Location.client_id == client_id)

    if active_only:
        query = query.where(Location.is_active == True)

    query = query.order_by(Location.region, Location.site_name)

    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{location_id}", response_model=LocationResponse)
async def get_location(
    location_id: UUID,
    db: DB,
    current_user: CurrentUser,
) -> Location:
    result = await db.execute(select(Location).where(Location.id == location_id))
    location = result.scalar_one_or_none()

    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found",
        )

    return location


@router.post("", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
async def create_location(
    location_data: LocationCreate,
    db: DB,
    current_user: CurrentAdmin,
) -> Location:
    location = Location(**location_data.model_dump())
    db.add(location)
    await db.commit()
    await db.refresh(location)
    return location


@router.patch("/{location_id}", response_model=LocationResponse)
async def update_location(
    location_id: UUID,
    location_data: LocationUpdate,
    db: DB,
    current_user: CurrentAdmin,
) -> Location:
    result = await db.execute(select(Location).where(Location.id == location_id))
    location = result.scalar_one_or_none()

    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found",
        )

    update_data = location_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(location, field, value)

    await db.commit()
    await db.refresh(location)
    return location


# Job Codes under locations
@router.get("/{location_id}/job-codes", response_model=list[JobCodeResponse])
async def list_job_codes(
    location_id: UUID,
    db: DB,
    current_user: CurrentUser,
    active_only: bool = True,
) -> list[JobCode]:
    query = select(JobCode).where(JobCode.location_id == location_id)

    if active_only:
        query = query.where(JobCode.is_active == True)

    query = query.order_by(JobCode.code)

    result = await db.execute(query)
    return list(result.scalars().all())


@router.post(
    "/{location_id}/job-codes",
    response_model=JobCodeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_job_code(
    location_id: UUID,
    job_code_data: JobCodeCreate,
    db: DB,
    current_user: CurrentAdmin,
) -> JobCode:
    # Verify location exists
    result = await db.execute(select(Location).where(Location.id == location_id))
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found",
        )

    job_code = JobCode(location_id=location_id, **job_code_data.model_dump(exclude={"location_id"}))
    db.add(job_code)
    await db.commit()
    await db.refresh(job_code)
    return job_code


# Flat job codes endpoint for easier frontend use
@router.get("/job-codes/all", response_model=list[JobCodeResponse])
async def list_all_job_codes(
    db: DB,
    current_user: CurrentUser,
    client_id: UUID | None = None,
    active_only: bool = True,
) -> list[JobCode]:
    """Get all job codes, optionally filtered by client."""
    query = select(JobCode).join(Location)

    if client_id:
        query = query.where(Location.client_id == client_id)

    if active_only:
        query = query.where(JobCode.is_active == True)
        query = query.where(Location.is_active == True)

    query = query.order_by(JobCode.code)

    result = await db.execute(query)
    return list(result.scalars().all())
