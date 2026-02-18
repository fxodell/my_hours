from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.client import Client
from app.schemas.client import ClientCreate, ClientUpdate, ClientResponse
from app.api.deps import DB, CurrentUser, CurrentAdmin

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[ClientResponse])
async def list_clients(
    db: DB,
    current_user: CurrentUser,
    active_only: bool = True,
) -> list[Client]:
    query = select(Client)
    if active_only:
        query = query.where(Client.is_active == True)
    query = query.order_by(Client.name)

    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: UUID,
    db: DB,
    current_user: CurrentUser,
) -> Client:
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    return client


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    client_data: ClientCreate,
    db: DB,
    current_user: CurrentAdmin,
) -> Client:
    client = Client(**client_data.model_dump())

    try:
        db.add(client)
        await db.commit()
        await db.refresh(client)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Client with this name already exists",
        )

    return client


@router.patch("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: UUID,
    client_data: ClientUpdate,
    db: DB,
    current_user: CurrentAdmin,
) -> Client:
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    update_data = client_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(client, field, value)

    try:
        await db.commit()
        await db.refresh(client)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Client with this name already exists",
        )

    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: UUID,
    db: DB,
    current_user: CurrentAdmin,
) -> None:
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    await db.delete(client)
    await db.commit()
