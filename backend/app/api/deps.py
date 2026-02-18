from typing import Annotated
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.employee import Employee

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Employee:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise credentials_exception

    result = await db.execute(select(Employee).where(Employee.id == user_uuid))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


async def get_current_active_user(
    current_user: Annotated[Employee, Depends(get_current_user)],
) -> Employee:
    return current_user


async def get_current_manager(
    current_user: Annotated[Employee, Depends(get_current_user)],
) -> Employee:
    if not current_user.is_manager and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager privileges required",
        )
    return current_user


async def get_current_admin(
    current_user: Annotated[Employee, Depends(get_current_user)],
) -> Employee:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


# Type aliases for cleaner route signatures
CurrentUser = Annotated[Employee, Depends(get_current_active_user)]
CurrentManager = Annotated[Employee, Depends(get_current_manager)]
CurrentAdmin = Annotated[Employee, Depends(get_current_admin)]
DB = Annotated[AsyncSession, Depends(get_db)]
