from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.service_type import ServiceType
from app.schemas.service_type import ServiceTypeCreate, ServiceTypeUpdate, ServiceTypeResponse
from app.api.deps import DB, CurrentUser, CurrentAdmin

router = APIRouter(prefix="/service-types", tags=["service-types"])


@router.get("", response_model=list[ServiceTypeResponse])
async def list_service_types(
    db: DB,
    current_user: CurrentUser,
) -> list[ServiceType]:
    result = await db.execute(select(ServiceType).order_by(ServiceType.name))
    return list(result.scalars().all())


@router.get("/{service_type_id}", response_model=ServiceTypeResponse)
async def get_service_type(
    service_type_id: UUID,
    db: DB,
    current_user: CurrentUser,
) -> ServiceType:
    result = await db.execute(
        select(ServiceType).where(ServiceType.id == service_type_id)
    )
    service_type = result.scalar_one_or_none()

    if not service_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service type not found",
        )

    return service_type


@router.post("", response_model=ServiceTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_service_type(
    service_type_data: ServiceTypeCreate,
    db: DB,
    current_user: CurrentAdmin,
) -> ServiceType:
    service_type = ServiceType(**service_type_data.model_dump())

    try:
        db.add(service_type)
        await db.commit()
        await db.refresh(service_type)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Service type with this name already exists",
        )

    return service_type


@router.patch("/{service_type_id}", response_model=ServiceTypeResponse)
async def update_service_type(
    service_type_id: UUID,
    service_type_data: ServiceTypeUpdate,
    db: DB,
    current_user: CurrentAdmin,
) -> ServiceType:
    result = await db.execute(
        select(ServiceType).where(ServiceType.id == service_type_id)
    )
    service_type = result.scalar_one_or_none()

    if not service_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service type not found",
        )

    update_data = service_type_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(service_type, field, value)

    try:
        await db.commit()
        await db.refresh(service_type)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Service type with this name already exists",
        )

    return service_type


@router.delete("/{service_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service_type(
    service_type_id: UUID,
    db: DB,
    current_user: CurrentAdmin,
) -> None:
    result = await db.execute(
        select(ServiceType).where(ServiceType.id == service_type_id)
    )
    service_type = result.scalar_one_or_none()

    if not service_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service type not found",
        )

    await db.delete(service_type)
    await db.commit()
