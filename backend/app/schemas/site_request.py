from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

from app.schemas.base import BaseSchema, TimestampSchema


class SiteRequestCreate(BaseSchema):
    client_id: UUID
    site_name: str
    region: Optional[str] = None
    job_code: Optional[str] = None
    job_code_description: Optional[str] = None
    notes: Optional[str] = None


class SiteRequestReject(BaseModel):
    rejection_reason: str


class SiteRequestResponse(TimestampSchema):
    id: UUID
    employee_id: UUID
    client_id: UUID
    site_name: str
    region: Optional[str] = None
    job_code: Optional[str] = None
    job_code_description: Optional[str] = None
    notes: Optional[str] = None
    status: str
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_location_id: Optional[UUID] = None
    created_job_code_id: Optional[UUID] = None
    employee_name: Optional[str] = None
    client_name: Optional[str] = None
    reviewer_name: Optional[str] = None
