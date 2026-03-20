"""Integration tests for admin CRUD endpoints (clients, service types, employees, locations, pay periods)."""

import pytest
import pytest_asyncio
from datetime import date
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.models.client import Client
from app.models.location import Location
from app.core.security import get_password_hash, create_access_token


@pytest.fixture
def _ctx():
    return {}


@pytest_asyncio.fixture(autouse=True)
async def seed(db_session: AsyncSession, _ctx: dict):
    admin = Employee(
        email="crud-admin@test.com", password_hash=get_password_hash("pass"),
        first_name="Admin", last_name="User",
        hire_date=date(2024, 1, 1), pay_period_group="A",
        is_admin=True, is_active=True,
    )
    emp = Employee(
        email="crud-emp@test.com", password_hash=get_password_hash("pass"),
        first_name="Regular", last_name="Employee",
        hire_date=date(2024, 1, 1), pay_period_group="A", is_active=True,
    )
    db_session.add_all([admin, emp])
    await db_session.flush()

    client_obj = Client(name="Test Client", industry="O&G", is_active=True)
    db_session.add(client_obj)
    await db_session.flush()

    loc = Location(client_id=client_obj.id, site_name="Test Site", region="TX", is_active=True)
    db_session.add(loc)
    await db_session.commit()

    _ctx.update({
        "admin_headers": {"Authorization": f"Bearer {create_access_token(data={'sub': str(admin.id), 'email': admin.email})}"},
        "emp_headers": {"Authorization": f"Bearer {create_access_token(data={'sub': str(emp.id), 'email': emp.email})}"},
        "client_id": str(client_obj.id),
        "location_id": str(loc.id),
    })


# --- Clients ---

@pytest.mark.asyncio
async def test_list_clients(client: AsyncClient, _ctx: dict):
    resp = await client.get("/api/clients", headers=_ctx["emp_headers"])
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_create_client(client: AsyncClient, _ctx: dict):
    resp = await client.post(
        "/api/clients",
        json={"name": "New Client", "industry": "Fiber"},
        headers=_ctx["admin_headers"],
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "New Client"


@pytest.mark.asyncio
async def test_create_client_requires_admin(client: AsyncClient, _ctx: dict):
    resp = await client.post(
        "/api/clients",
        json={"name": "Unauthorized Client"},
        headers=_ctx["emp_headers"],
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_duplicate_client(client: AsyncClient, _ctx: dict):
    resp = await client.post(
        "/api/clients",
        json={"name": "Test Client"},
        headers=_ctx["admin_headers"],
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_update_client(client: AsyncClient, _ctx: dict):
    resp = await client.patch(
        f"/api/clients/{_ctx['client_id']}",
        json={"industry": "Power"},
        headers=_ctx["admin_headers"],
    )
    assert resp.status_code == 200
    assert resp.json()["industry"] == "Power"


@pytest.mark.asyncio
async def test_delete_client_soft(client: AsyncClient, _ctx: dict):
    """Delete should soft-deactivate, not hard-delete."""
    resp = await client.delete(
        f"/api/clients/{_ctx['client_id']}",
        headers=_ctx["admin_headers"],
    )
    assert resp.status_code == 204

    # Should not appear in active-only list
    resp = await client.get("/api/clients", headers=_ctx["admin_headers"])
    ids = [c["id"] for c in resp.json()]
    assert _ctx["client_id"] not in ids

    # Should appear when including inactive
    resp = await client.get("/api/clients?active_only=false", headers=_ctx["admin_headers"])
    ids = [c["id"] for c in resp.json()]
    assert _ctx["client_id"] in ids


# --- Service Types ---

@pytest.mark.asyncio
async def test_create_service_type(client: AsyncClient, _ctx: dict):
    resp = await client.post(
        "/api/service-types",
        json={"name": "SCADA Services", "is_billable": True},
        headers=_ctx["admin_headers"],
    )
    assert resp.status_code == 201
    st_id = resp.json()["id"]

    # Update
    resp = await client.patch(
        f"/api/service-types/{st_id}",
        json={"is_billable": False},
        headers=_ctx["admin_headers"],
    )
    assert resp.status_code == 200
    assert resp.json()["is_billable"] is False


@pytest.mark.asyncio
async def test_delete_service_type_soft(client: AsyncClient, _ctx: dict):
    """Delete should soft-deactivate."""
    # Create one first
    resp = await client.post(
        "/api/service-types",
        json={"name": "To Delete ST"},
        headers=_ctx["admin_headers"],
    )
    st_id = resp.json()["id"]

    resp = await client.delete(f"/api/service-types/{st_id}", headers=_ctx["admin_headers"])
    assert resp.status_code == 204

    # Should not appear in active-only list
    resp = await client.get("/api/service-types", headers=_ctx["admin_headers"])
    ids = [s["id"] for s in resp.json()]
    assert st_id not in ids

    # Should appear when including inactive
    resp = await client.get("/api/service-types?active_only=false", headers=_ctx["admin_headers"])
    ids = [s["id"] for s in resp.json()]
    assert st_id in ids


# --- Employees ---

@pytest.mark.asyncio
async def test_create_employee(client: AsyncClient, _ctx: dict):
    resp = await client.post(
        "/api/employees",
        json={
            "email": "new-crud@test.com",
            "password": "password123",
            "first_name": "New",
            "last_name": "Person",
            "hire_date": "2024-06-01",
            "pay_period_group": "B",
        },
        headers=_ctx["admin_headers"],
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == "new-crud@test.com"


@pytest.mark.asyncio
async def test_create_employee_requires_admin(client: AsyncClient, _ctx: dict):
    resp = await client.post(
        "/api/employees",
        json={
            "email": "unauth@test.com", "password": "pass",
            "first_name": "X", "last_name": "Y",
            "hire_date": "2024-01-01", "pay_period_group": "A",
        },
        headers=_ctx["emp_headers"],
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_employee_list_hides_rate(client: AsyncClient, _ctx: dict):
    """Regular employees see summary response (no hourly_rate)."""
    resp = await client.get("/api/employees", headers=_ctx["emp_headers"])
    assert resp.status_code == 200
    for e in resp.json():
        assert "hourly_rate" not in e


@pytest.mark.asyncio
async def test_employee_list_shows_rate_for_admin(client: AsyncClient, _ctx: dict):
    """Admins see full response (with hourly_rate)."""
    resp = await client.get("/api/employees", headers=_ctx["admin_headers"])
    assert resp.status_code == 200
    for e in resp.json():
        assert "hourly_rate" in e


# --- Locations ---

@pytest.mark.asyncio
async def test_create_location(client: AsyncClient, _ctx: dict):
    resp = await client.post(
        "/api/locations",
        json={
            "client_id": _ctx["client_id"],
            "site_name": "New Site",
            "region": "OK",
        },
        headers=_ctx["admin_headers"],
    )
    assert resp.status_code == 201
    assert resp.json()["site_name"] == "New Site"


@pytest.mark.asyncio
async def test_delete_location_soft(client: AsyncClient, _ctx: dict):
    """Delete should soft-deactivate."""
    resp = await client.delete(
        f"/api/locations/{_ctx['location_id']}",
        headers=_ctx["admin_headers"],
    )
    assert resp.status_code == 204

    # Not in active list
    resp = await client.get("/api/locations", headers=_ctx["admin_headers"])
    ids = [l["id"] for l in resp.json()]
    assert _ctx["location_id"] not in ids


@pytest.mark.asyncio
async def test_list_locations_pagination(client: AsyncClient, _ctx: dict):
    """Limit/offset params work."""
    resp = await client.get("/api/locations?limit=1&offset=0", headers=_ctx["admin_headers"])
    assert resp.status_code == 200
    assert len(resp.json()) <= 1


# --- Pay Periods ---

@pytest.mark.asyncio
async def test_generate_pay_periods(client: AsyncClient, _ctx: dict):
    """Admin can generate weekly pay periods."""
    resp = await client.post(
        "/api/pay-periods/generate",
        params={"start_date": "2026-05-03", "weeks": 2, "period_group": "A"},
        headers=_ctx["admin_headers"],
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_generate_requires_sunday(client: AsyncClient, _ctx: dict):
    """Start date must be a Sunday."""
    resp = await client.post(
        "/api/pay-periods/generate",
        params={"start_date": "2026-05-04", "weeks": 1, "period_group": "A"},
        headers=_ctx["admin_headers"],
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_generate_invalid_group(client: AsyncClient, _ctx: dict):
    resp = await client.post(
        "/api/pay-periods/generate",
        params={"start_date": "2026-05-03", "weeks": 1, "period_group": "X"},
        headers=_ctx["admin_headers"],
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_close_pay_period(client: AsyncClient, _ctx: dict):
    """Admin can close a pay period."""
    # Generate a period first
    resp = await client.post(
        "/api/pay-periods/generate",
        params={"start_date": "2026-06-28", "weeks": 1, "period_group": "B"},
        headers=_ctx["admin_headers"],
    )
    pp_id = resp.json()[0]["id"]

    resp = await client.post(
        f"/api/pay-periods/{pp_id}/close",
        headers=_ctx["admin_headers"],
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"
