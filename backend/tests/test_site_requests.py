"""Tests for site request endpoints."""

from datetime import date, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete

from app.models.company import Company
from app.models.client import Client
from app.models.location import Location
from app.models.job_code import JobCode
from app.models.pay_period import PayPeriod


@pytest_asyncio.fixture
async def test_client_record(db_session: AsyncSession, test_company: Company) -> Client:
    """Create a test client for site requests."""
    # Ensure unique constraint on Client.name does not fail across tests.
    await db_session.execute(delete(Client).where(Client.name == "Test Oil Co"))
    client = Client(company_id=test_company.id, name="Test Oil Co", industry="Oil & Gas", is_active=True)
    db_session.add(client)
    await db_session.flush()
    await db_session.refresh(client)
    return client


# --- Create ---

@pytest.mark.asyncio
async def test_create_site_request(
    client: AsyncClient,
    auth_headers: dict,
    test_client_record: Client,
):
    response = await client.post(
        "/api/site-requests",
        json={
            "client_id": str(test_client_record.id),
            "site_name": "New Well Pad A",
            "region": "Alpine High",
            "job_code": "AFE-12345",
            "job_code_description": "Drilling operations",
            "notes": "New well starting next week",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["site_name"] == "New Well Pad A"
    assert data["status"] == "pending"
    assert data["region"] == "Alpine High"
    assert data["job_code"] == "AFE-12345"
    assert data["notes"] == "New well starting next week"


@pytest.mark.asyncio
async def test_create_site_request_minimal(
    client: AsyncClient,
    auth_headers: dict,
    test_client_record: Client,
):
    response = await client.post(
        "/api/site-requests",
        json={
            "client_id": str(test_client_record.id),
            "site_name": "Simple Site",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["site_name"] == "Simple Site"
    assert data["job_code"] is None


@pytest.mark.asyncio
async def test_create_site_request_invalid_client(
    client: AsyncClient,
    auth_headers: dict,
):
    response = await client.post(
        "/api/site-requests",
        json={
            "client_id": "00000000-0000-0000-0000-000000000000",
            "site_name": "Nowhere",
        },
        headers=auth_headers,
    )
    assert response.status_code == 404


# --- List ---

@pytest.mark.asyncio
async def test_list_own_requests(
    client: AsyncClient,
    auth_headers: dict,
    test_client_record: Client,
):
    # Create a request first
    await client.post(
        "/api/site-requests",
        json={"client_id": str(test_client_record.id), "site_name": "My Site"},
        headers=auth_headers,
    )

    response = await client.get("/api/site-requests", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(r["site_name"] == "My Site" for r in data)


@pytest.mark.asyncio
async def test_manager_sees_all_requests(
    client: AsyncClient,
    auth_headers: dict,
    manager_auth_headers: dict,
    test_client_record: Client,
):
    # Employee creates a request
    await client.post(
        "/api/site-requests",
        json={"client_id": str(test_client_record.id), "site_name": "Employee Site"},
        headers=auth_headers,
    )

    # Manager can see it
    response = await client.get("/api/site-requests", headers=manager_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert any(r["site_name"] == "Employee Site" for r in data)


@pytest.mark.asyncio
async def test_filter_by_status(
    client: AsyncClient,
    auth_headers: dict,
    test_client_record: Client,
):
    await client.post(
        "/api/site-requests",
        json={"client_id": str(test_client_record.id), "site_name": "Pending Site"},
        headers=auth_headers,
    )

    response = await client.get(
        "/api/site-requests?status_filter=pending", headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert all(r["status"] == "pending" for r in data)


# --- Approve ---

@pytest.mark.asyncio
async def test_approve_creates_location(
    client: AsyncClient,
    auth_headers: dict,
    manager_auth_headers: dict,
    test_client_record: Client,
):
    # Create request
    create_resp = await client.post(
        "/api/site-requests",
        json={
            "client_id": str(test_client_record.id),
            "site_name": "Approved Site",
            "region": "Permian",
        },
        headers=auth_headers,
    )
    request_id = create_resp.json()["id"]

    # Approve
    response = await client.post(
        f"/api/site-requests/{request_id}/approve",
        headers=manager_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "approved"
    assert data["created_location_id"] is not None
    assert data["reviewed_by"] is not None


@pytest.mark.asyncio
async def test_approve_creates_job_code(
    client: AsyncClient,
    auth_headers: dict,
    manager_auth_headers: dict,
    test_client_record: Client,
):
    create_resp = await client.post(
        "/api/site-requests",
        json={
            "client_id": str(test_client_record.id),
            "site_name": "JC Site",
            "job_code": "AFE-99999",
            "job_code_description": "New AFE",
        },
        headers=auth_headers,
    )
    request_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/site-requests/{request_id}/approve",
        headers=manager_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["created_job_code_id"] is not None


@pytest.mark.asyncio
async def test_approve_duplicate_location_reuses_existing(
    client: AsyncClient,
    auth_headers: dict,
    manager_auth_headers: dict,
    test_client_record: Client,
    db_session: AsyncSession,
):
    # Pre-create a location
    existing = Location(
        company_id=test_client_record.company_id,
        client_id=test_client_record.id,
        site_name="Existing Site",
        is_active=True,
    )
    db_session.add(existing)
    await db_session.commit()
    await db_session.refresh(existing)

    # Request with same name
    create_resp = await client.post(
        "/api/site-requests",
        json={
            "client_id": str(test_client_record.id),
            "site_name": "Existing Site",
        },
        headers=auth_headers,
    )
    request_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/site-requests/{request_id}/approve",
        headers=manager_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    # Should reuse existing location
    assert data["created_location_id"] == str(existing.id)


# --- Reject ---

@pytest.mark.asyncio
async def test_reject_stores_reason(
    client: AsyncClient,
    auth_headers: dict,
    manager_auth_headers: dict,
    test_client_record: Client,
):
    create_resp = await client.post(
        "/api/site-requests",
        json={
            "client_id": str(test_client_record.id),
            "site_name": "Reject Me",
        },
        headers=auth_headers,
    )
    request_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/site-requests/{request_id}/reject",
        json={"rejection_reason": "Site already exists under different name"},
        headers=manager_auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"
    assert data["rejection_reason"] == "Site already exists under different name"


# --- Permission checks ---

@pytest.mark.asyncio
async def test_employee_cannot_approve(
    client: AsyncClient,
    auth_headers: dict,
    test_client_record: Client,
):
    create_resp = await client.post(
        "/api/site-requests",
        json={
            "client_id": str(test_client_record.id),
            "site_name": "No Approve",
        },
        headers=auth_headers,
    )
    request_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/site-requests/{request_id}/approve",
        headers=auth_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_employee_cannot_reject(
    client: AsyncClient,
    auth_headers: dict,
    test_client_record: Client,
):
    create_resp = await client.post(
        "/api/site-requests",
        json={
            "client_id": str(test_client_record.id),
            "site_name": "No Reject",
        },
        headers=auth_headers,
    )
    request_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/site-requests/{request_id}/reject",
        json={"rejection_reason": "nope"},
        headers=auth_headers,
    )
    assert response.status_code == 403


# --- Delete ---

@pytest.mark.asyncio
async def test_manager_can_delete_approved_request(
    client: AsyncClient,
    auth_headers: dict,
    manager_auth_headers: dict,
    test_client_record: Client,
):
    create_resp = await client.post(
        "/api/site-requests",
        json={"client_id": str(test_client_record.id), "site_name": "Delete Me"},
        headers=auth_headers,
    )
    request_id = create_resp.json()["id"]

    # Approve first
    await client.post(
        f"/api/site-requests/{request_id}/approve",
        headers=manager_auth_headers,
    )

    # Delete
    response = await client.delete(
        f"/api/site-requests/{request_id}",
        headers=manager_auth_headers,
    )
    assert response.status_code == 204

    # Verify gone
    list_resp = await client.get("/api/site-requests", headers=manager_auth_headers)
    assert not any(r["id"] == request_id for r in list_resp.json())


@pytest.mark.asyncio
async def test_employee_cannot_delete_request(
    client: AsyncClient,
    auth_headers: dict,
    test_client_record: Client,
):
    create_resp = await client.post(
        "/api/site-requests",
        json={"client_id": str(test_client_record.id), "site_name": "No Delete"},
        headers=auth_headers,
    )
    request_id = create_resp.json()["id"]

    response = await client.delete(
        f"/api/site-requests/{request_id}",
        headers=auth_headers,
    )
    assert response.status_code == 403


# --- Cannot re-process ---

@pytest.mark.asyncio
async def test_cannot_approve_already_approved(
    client: AsyncClient,
    auth_headers: dict,
    manager_auth_headers: dict,
    test_client_record: Client,
):
    create_resp = await client.post(
        "/api/site-requests",
        json={
            "client_id": str(test_client_record.id),
            "site_name": "Double Approve",
        },
        headers=auth_headers,
    )
    request_id = create_resp.json()["id"]

    # First approve
    await client.post(
        f"/api/site-requests/{request_id}/approve",
        headers=manager_auth_headers,
    )

    # Second approve should fail
    response = await client.post(
        f"/api/site-requests/{request_id}/approve",
        headers=manager_auth_headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_cannot_reject_already_rejected(
    client: AsyncClient,
    auth_headers: dict,
    manager_auth_headers: dict,
    test_client_record: Client,
):
    create_resp = await client.post(
        "/api/site-requests",
        json={
            "client_id": str(test_client_record.id),
            "site_name": "Double Reject",
        },
        headers=auth_headers,
    )
    request_id = create_resp.json()["id"]

    await client.post(
        f"/api/site-requests/{request_id}/reject",
        json={"rejection_reason": "reason 1"},
        headers=manager_auth_headers,
    )

    response = await client.post(
        f"/api/site-requests/{request_id}/reject",
        json={"rejection_reason": "reason 2"},
        headers=manager_auth_headers,
    )
    assert response.status_code == 400


# --- End-to-end: approve then use in time entry ---

@pytest.mark.asyncio
async def test_approve_then_use_location_and_job_code_in_time_entry(
    client: AsyncClient,
    auth_headers: dict,
    manager_auth_headers: dict,
    test_client_record: Client,
    test_user,
    db_session: AsyncSession,
):
    # 1. Employee submits location request with job code
    create_resp = await client.post(
        "/api/site-requests",
        json={
            "client_id": str(test_client_record.id),
            "site_name": "E2E Site",
            "region": "Permian",
            "job_code": "AFE-E2E",
            "job_code_description": "End to end test",
        },
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    request_id = create_resp.json()["id"]

    # 2. Manager approves
    approve_resp = await client.post(
        f"/api/site-requests/{request_id}/approve",
        headers=manager_auth_headers,
    )
    assert approve_resp.status_code == 200
    approved = approve_resp.json()
    location_id = approved["created_location_id"]
    job_code_id = approved["created_job_code_id"]
    assert location_id is not None
    assert job_code_id is not None

    # 3. Verify location appears in locations list for the client
    loc_resp = await client.get(
        f"/api/locations?client_id={test_client_record.id}",
        headers=auth_headers,
    )
    assert loc_resp.status_code == 200
    locations = loc_resp.json()
    assert any(l["id"] == location_id for l in locations)

    # 4. Verify job code appears for that location
    jc_resp = await client.get(
        f"/api/locations/{location_id}/job-codes",
        headers=auth_headers,
    )
    assert jc_resp.status_code == 200
    job_codes = jc_resp.json()
    assert any(jc["id"] == job_code_id for jc in job_codes)
    assert any(jc["code"] == "AFE-E2E" for jc in job_codes)

    # 5. Create a pay period + timesheet so we can add a time entry
    today = date.today()
    start_date = today - timedelta(days=7)
    end_date = today + timedelta(days=6)
    await db_session.execute(
        delete(PayPeriod).where(
            PayPeriod.period_group == test_user.pay_period_group,
            PayPeriod.start_date == start_date,
        )
    )
    pay_period = PayPeriod(
        company_id=test_user.company_id,
        period_group=test_user.pay_period_group,
        start_date=start_date,
        end_date=end_date,
        status="open",
    )
    db_session.add(pay_period)
    await db_session.commit()

    ts_resp = await client.get("/api/timesheets/current", headers=auth_headers)
    assert ts_resp.status_code == 200
    timesheet_id = ts_resp.json()["id"]

    # 6. Create time entry using the approved location + job code
    entry_resp = await client.post(
        f"/api/timesheets/{timesheet_id}/entries",
        headers=auth_headers,
        json={
            "work_date": today.isoformat(),
            "work_mode": "on_site",
            "hours": 8,
            "description": "E2E test work",
            "client_id": str(test_client_record.id),
            "location_id": location_id,
            "job_code_id": job_code_id,
        },
    )
    assert entry_resp.status_code == 201
    entry = entry_resp.json()
    assert entry["location_id"] == location_id
    assert entry["job_code_id"] == job_code_id
    assert float(entry["hours"]) == 8
