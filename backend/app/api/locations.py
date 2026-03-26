from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.location import Location
from app.models.job_code import JobCode
from app.schemas.location import LocationCreate, LocationUpdate, LocationResponse, JobCodeBrief
from app.schemas.job_code import JobCodeCreate, JobCodeUpdate, JobCodeResponse
from app.api.deps import DB, CurrentUser, CurrentAdmin, resolve_company_id

router = APIRouter(prefix="/locations", tags=["locations"])


def location_to_response(loc: Location) -> LocationResponse:
    jcs = [JobCodeBrief.model_validate(j) for j in loc.job_codes if j.is_active]
    return LocationResponse(
        id=loc.id,
        client_id=loc.client_id,
        region=loc.region,
        site_name=loc.site_name,
        site_code=loc.site_code,
        latitude=loc.latitude,
        longitude=loc.longitude,
        is_active=loc.is_active,
        created_at=loc.created_at,
        updated_at=loc.updated_at,
        job_codes=jcs,
    )


async def _load_location_with_job_codes(db: DB, location_id: UUID, company_id: UUID) -> Location | None:
    result = await db.execute(
        select(Location)
        .options(selectinload(Location.job_codes))
        .where(Location.id == location_id, Location.company_id == company_id),
    )
    return result.scalar_one_or_none()


@router.get("", response_model=list[LocationResponse])
async def list_locations(
    db: DB,
    current_user: CurrentUser,
    client_id: UUID | None = None,
    active_only: bool = True,
    limit: int = 10000,
    offset: int = 0,
    company_id: UUID | None = None,
) -> list[LocationResponse]:
    cid = resolve_company_id(current_user, company_id)
    query = select(Location).options(selectinload(Location.job_codes)).where(Location.company_id == cid)

    if client_id:
        query = query.where(Location.client_id == client_id)

    if active_only:
        query = query.where(Location.is_active == True)

    query = query.order_by(Location.region, Location.site_name).offset(offset).limit(limit)

    result = await db.execute(query)
    locations = list(result.scalars().unique().all())
    return [location_to_response(loc) for loc in locations]


@router.get("/{location_id}", response_model=LocationResponse)
async def get_location(
    location_id: UUID,
    db: DB,
    current_user: CurrentUser,
) -> LocationResponse:
    location = await _load_location_with_job_codes(db, location_id, current_user.company_id)
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found",
        )
    return location_to_response(location)


@router.post("", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
async def create_location(
    location_data: LocationCreate,
    db: DB,
    current_user: CurrentAdmin,
) -> LocationResponse:
    location = Location(company_id=current_user.company_id, **location_data.model_dump())
    db.add(location)
    await db.commit()
    loc_full = await _load_location_with_job_codes(db, location.id, current_user.company_id)
    assert loc_full is not None
    return location_to_response(loc_full)


@router.patch("/{location_id}", response_model=LocationResponse)
async def update_location(
    location_id: UUID,
    location_data: LocationUpdate,
    db: DB,
    current_user: CurrentAdmin,
) -> LocationResponse:
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
    loc_full = await _load_location_with_job_codes(db, location_id, current_user.company_id)
    assert loc_full is not None
    return location_to_response(loc_full)


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
            detail="Site code not found",
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
    """Get all site codes, optionally filtered by client."""
    query = select(JobCode).join(Location).where(JobCode.company_id == current_user.company_id)

    if client_id:
        query = query.where(Location.client_id == client_id)

    if active_only:
        query = query.where(JobCode.is_active == True)
        query = query.where(Location.is_active == True)

    query = query.order_by(JobCode.code)

    result = await db.execute(query)
    return list(result.scalars().all())
