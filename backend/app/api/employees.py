from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.employee import Employee
from app.schemas.employee import EmployeeCreate, EmployeeUpdate, EmployeeResponse
from app.core.security import get_password_hash
from app.api.deps import DB, CurrentUser, CurrentAdmin

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("", response_model=list[EmployeeResponse])
async def list_employees(
    db: DB,
    current_user: CurrentUser,
    active_only: bool = True,
) -> list[Employee]:
    query = select(Employee)
    if active_only:
        query = query.where(Employee.is_active == True)
    query = query.order_by(Employee.last_name, Employee.first_name)

    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: UUID,
    db: DB,
    current_user: CurrentUser,
) -> Employee:
    result = await db.execute(select(Employee).where(Employee.id == employee_id))
    employee = result.scalar_one_or_none()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    return employee


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    employee_data: EmployeeCreate,
    db: DB,
    current_user: CurrentAdmin,
) -> Employee:
    data = employee_data.model_dump(exclude={"password"})
    data["password_hash"] = get_password_hash(employee_data.password)

    employee = Employee(**data)

    try:
        db.add(employee)
        await db.commit()
        await db.refresh(employee)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Employee with this email already exists",
        )

    return employee


@router.patch("/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: UUID,
    employee_data: EmployeeUpdate,
    db: DB,
    current_user: CurrentAdmin,
) -> Employee:
    result = await db.execute(select(Employee).where(Employee.id == employee_id))
    employee = result.scalar_one_or_none()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    update_data = employee_data.model_dump(exclude_unset=True)

    # Handle password separately
    if "password" in update_data:
        update_data["password_hash"] = get_password_hash(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(employee, field, value)

    try:
        await db.commit()
        await db.refresh(employee)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Employee with this email already exists",
        )

    return employee


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(
    employee_id: UUID,
    db: DB,
    current_user: CurrentAdmin,
) -> None:
    result = await db.execute(select(Employee).where(Employee.id == employee_id))
    employee = result.scalar_one_or_none()

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    # Soft delete - set inactive instead of removing
    employee.is_active = False
    await db.commit()
