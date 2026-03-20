"""Site request API endpoints."""

from datetime import datetime, timezone
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from sqlalchemy import select, and_

from app.api.deps import CurrentUser, CurrentManager, DB
from app.models.site_request import SiteRequest
from app.models.client import Client
from app.models.location import Location
from app.models.job_code import JobCode
from app.models.employee import Employee
from app.schemas.site_request import SiteRequestCreate, SiteRequestReject, SiteRequestResponse
from app.services.email import email_service

router = APIRouter(prefix="/site-requests", tags=["site-requests"])


def _to_response(req: SiteRequest, employee_name: str = None, client_name: str = None, reviewer_name: str = None) -> dict:
    """Convert a SiteRequest + joined names into a response dict."""
    data = {
        "id": req.id,
        "employee_id": req.employee_id,
        "client_id": req.client_id,
        "site_name": req.site_name,
        "region": req.region,
        "job_code": req.job_code,
        "job_code_description": req.job_code_description,
        "notes": req.notes,
        "status": req.status,
        "reviewed_by": req.reviewed_by,
        "reviewed_at": req.reviewed_at,
        "rejection_reason": req.rejection_reason,
        "created_location_id": req.created_location_id,
        "created_job_code_id": req.created_job_code_id,
        "created_at": req.created_at,
        "updated_at": req.updated_at,
        "employee_name": employee_name,
        "client_name": client_name,
        "reviewer_name": reviewer_name,
    }
    return data


@router.post("", response_model=SiteRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_site_request(
    data: SiteRequestCreate,
    db: DB,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
) -> dict:
    # Verify client exists
    result = await db.execute(select(Client).where(Client.id == data.client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    site_request = SiteRequest(
        employee_id=current_user.id,
        client_id=data.client_id,
        site_name=data.site_name,
        region=data.region,
        job_code=data.job_code,
        job_code_description=data.job_code_description,
        notes=data.notes,
        status="pending",
    )
    db.add(site_request)
    await db.commit()
    await db.refresh(site_request)

    # Notify managers in background
    background_tasks.add_task(
        email_service.send_site_request_submitted,
        current_user.full_name,
        client.name,
        data.site_name,
    )

    return _to_response(site_request, employee_name=current_user.full_name, client_name=client.name)


@router.get("", response_model=list[SiteRequestResponse])
async def list_site_requests(
    db: DB,
    current_user: CurrentUser,
    status_filter: Optional[str] = None,
) -> list[dict]:
    query = (
        select(SiteRequest, Employee, Client)
        .join(Employee, SiteRequest.employee_id == Employee.id)
        .join(Client, SiteRequest.client_id == Client.id)
    )

    # Non-managers only see their own requests
    if not current_user.is_manager and not current_user.is_admin:
        query = query.where(SiteRequest.employee_id == current_user.id)

    if status_filter:
        query = query.where(SiteRequest.status == status_filter)

    query = query.order_by(SiteRequest.created_at.desc())
    result = await db.execute(query)
    rows = result.all()

    responses = []
    for req, employee, client in rows:
        responses.append(_to_response(req, employee_name=employee.full_name, client_name=client.name))
    return responses


@router.post("/{request_id}/approve", response_model=SiteRequestResponse)
async def approve_site_request(
    request_id: UUID,
    db: DB,
    current_user: CurrentManager,
    background_tasks: BackgroundTasks,
) -> dict:
    result = await db.execute(
        select(SiteRequest, Employee, Client)
        .join(Employee, SiteRequest.employee_id == Employee.id)
        .join(Client, SiteRequest.client_id == Client.id)
        .where(SiteRequest.id == request_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site request not found")

    site_request, employee, client = row

    if site_request.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve request with status '{site_request.status}'",
        )

    # Check for duplicate location (same client + site_name)
    dup_result = await db.execute(
        select(Location).where(
            and_(
                Location.client_id == site_request.client_id,
                Location.site_name == site_request.site_name,
            )
        )
    )
    existing_location = dup_result.scalar_one_or_none()

    if existing_location:
        location = existing_location
    else:
        location = Location(
            client_id=site_request.client_id,
            site_name=site_request.site_name,
            region=site_request.region,
            is_active=True,
        )
        db.add(location)
        await db.flush()

    created_job_code = None
    if site_request.job_code:
        # Check for duplicate job code on this location
        dup_jc = await db.execute(
            select(JobCode).where(
                and_(
                    JobCode.location_id == location.id,
                    JobCode.code == site_request.job_code,
                )
            )
        )
        existing_jc = dup_jc.scalar_one_or_none()
        if existing_jc:
            created_job_code = existing_jc
        else:
            created_job_code = JobCode(
                location_id=location.id,
                code=site_request.job_code,
                description=site_request.job_code_description,
                is_active=True,
            )
            db.add(created_job_code)
            await db.flush()

    site_request.status = "approved"
    site_request.reviewed_by = current_user.id
    site_request.reviewed_at = datetime.now(timezone.utc)
    site_request.rejection_reason = None
    site_request.created_location_id = location.id
    if created_job_code:
        site_request.created_job_code_id = created_job_code.id

    await db.commit()
    await db.refresh(site_request)

    # Notify employee
    background_tasks.add_task(
        email_service.send_site_request_approved,
        employee.email,
        employee.full_name,
        site_request.site_name,
        current_user.full_name,
    )

    return _to_response(
        site_request,
        employee_name=employee.full_name,
        client_name=client.name,
        reviewer_name=current_user.full_name,
    )


@router.post("/{request_id}/reject", response_model=SiteRequestResponse)
async def reject_site_request(
    request_id: UUID,
    body: SiteRequestReject,
    db: DB,
    current_user: CurrentManager,
    background_tasks: BackgroundTasks,
) -> dict:
    result = await db.execute(
        select(SiteRequest, Employee, Client)
        .join(Employee, SiteRequest.employee_id == Employee.id)
        .join(Client, SiteRequest.client_id == Client.id)
        .where(SiteRequest.id == request_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site request not found")

    site_request, employee, client = row

    if site_request.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject request with status '{site_request.status}'",
        )

    site_request.status = "rejected"
    site_request.reviewed_by = current_user.id
    site_request.reviewed_at = datetime.now(timezone.utc)
    site_request.rejection_reason = body.rejection_reason

    await db.commit()
    await db.refresh(site_request)

    # Notify employee
    background_tasks.add_task(
        email_service.send_site_request_rejected,
        employee.email,
        employee.full_name,
        site_request.site_name,
        current_user.full_name,
        body.rejection_reason,
    )

    return _to_response(
        site_request,
        employee_name=employee.full_name,
        client_name=client.name,
        reviewer_name=current_user.full_name,
    )
