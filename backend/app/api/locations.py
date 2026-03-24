from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.models.location import Location
from app.models.job_code import JobCode
from app.schemas.location import LocationCreate, LocationUpdate, LocationResponse
from app.schemas.job_code import JobCodeCreate, JobCodeUpdate, JobCodeResponse
from app.api.deps import DB, CurrentUser, CurrentAdmin, resolve_company_id

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("", response_model=list[LocationResponse])
async def list_locations(
    db: DB,
    current_user: CurrentUser,
    client_id: UUID | None = None,
    active_only: bool = True,
    limit: int = 200,
    offset: int = 0,
    company_id: UUID | None = None,
) -> list[Location]:
    cid = resolve_company_id(current_user, company_id)
    query = select(Location).where(Location.company_id == cid)

    if client_id:
        query = query.where(Location.client_id == client_id)

    if active_only:
        query = query.where(Location.is_active == True)

    query = query.order_by(Location.region, Location.site_name).offset(offset).limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{location_id}", response_model=LocationResponse)
async def get_location(
    location_id: UUID,
    db: DB,
    current_user: CurrentUser,
) -> Location:
    result = await db.execute(
        select(Location).where(Location.id == location_id, Location.company_id == current_user.company_id)
    )
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
    location = Location(company_id=current_user.company_id, **location_data.model_dump())
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
    result = await db.execute(
        select(Location).where(Location.id == location_id, Location.company_id == current_user.company_id)
    )
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


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(
    location_id: UUID,
    db: DB,
    current_user: CurrentAdmin,
) -> None:
    result = await db.execute(
        select(Location).where(Location.id == location_id, Location.company_id == current_user.company_id)
    )
    location = result.scalar_one_or_none()

    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found",
        )

    # Soft delete - set inactive instead of removing
    location.is_active = False
    await db.commit()


# Job Codes under locations
@router.get("/{location_id}/job-codes", response_model=list[JobCodeResponse])
async def list_job_codes(
    location_id: UUID,
    db: DB,
    current_user: CurrentUser,
    active_only: bool = True,
) -> list[JobCode]:
    query = select(JobCode).where(JobCode.location_id == location_id, JobCode.company_id == current_user.company_id)

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
    # Verify location exists and belongs to same company
    result = await db.execute(
        select(Location).where(Location.id == location_id, Location.company_id == current_user.company_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found",
        )

    job_code = JobCode(company_id=current_user.company_id, location_id=location_id, **job_code_data.model_dump(exclude={"location_id"}))
    db.add(job_code)
    await db.commit()
    await db.refresh(job_code)
    return job_code


@router.delete("/{location_id}/job-codes/{job_code_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job_code(
    location_id: UUID,
    job_code_id: UUID,
    db: DB,
    current_user: CurrentAdmin,
) -> None:
    result = await db.execute(
        select(JobCode)
        .where(JobCode.id == job_code_id)
        .where(JobCode.location_id == location_id)
        .where(JobCode.company_id == current_user.company_id)
    )
    job_code = result.scalar_one_or_none()

    if not job_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job code not found",
        )

    # Soft delete - set inactive instead of removing
    job_code.is_active = False
    await db.commit()


# Flat job codes endpoint for easier frontend use
@router.get("/job-codes/all", response_model=list[JobCodeResponse])
async def list_all_job_codes(
    db: DB,
    current_user: CurrentUser,
    client_id: UUID | None = None,
    active_only: bool = True,
) -> list[JobCode]:
    """Get all job codes, optionally filtered by client."""
    query = select(JobCode).join(Location).where(JobCode.company_id == current_user.company_id)

    if client_id:
        query = query.where(Location.client_id == client_id)

    if active_only:
        query = query.where(JobCode.is_active == True)
        query = query.where(Location.is_active == True)

    query = query.order_by(JobCode.code)

    result = await db.execute(query)
    return list(result.scalars().all())
