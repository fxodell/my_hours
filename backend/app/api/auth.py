import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_password, create_access_token, get_password_hash
from app.core.config import settings
from app.models.employee import Employee
from app.schemas.auth import Token
from app.schemas.employee import EmployeeResponse
from app.api.deps import CurrentUser

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    result = await db.execute(
        select(Employee).where(Employee.email == form_data.username)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=access_token_expires,
    )

    return Token(access_token=access_token)


@router.get("/me", response_model=EmployeeResponse)
async def get_current_user_info(current_user: CurrentUser) -> Employee:
    return current_user


@router.post("/change-password")
async def change_password(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_password: str,
    new_password: str,
) -> dict:
    if not verify_password(current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.password_hash = get_password_hash(new_password)
    await db.commit()

    return {"message": "Password changed successfully"}


@router.post("/request-reset")
async def request_password_reset(
    email: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Request a password reset token. In production, this would send an email."""
    result = await db.execute(
        select(Employee).where(Employee.email == email)
    )
    user = result.scalar_one_or_none()

    # Always return success to prevent email enumeration
    if not user or not user.is_active:
        return {"message": "If an account with that email exists, a reset link has been sent."}

    # Generate reset token
    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
    await db.commit()

    # In production, send email with token
    # For development, log the token
    print(f"Password reset token for {email}: {token}")

    return {"message": "If an account with that email exists, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(
    token: str,
    new_password: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Reset password using a reset token."""
    result = await db.execute(
        select(Employee).where(Employee.reset_token == token)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    if user.reset_token_expires and user.reset_token_expires < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired",
        )

    if len(new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters",
        )

    user.password_hash = get_password_hash(new_password)
    user.reset_token = None
    user.reset_token_expires = None
    await db.commit()

    return {"message": "Password has been reset successfully"}
