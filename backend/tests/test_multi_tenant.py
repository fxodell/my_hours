"""Multi-tenant isolation tests.

Verifies that users from one company cannot access data from another company.
"""

import pytest
import pytest_asyncio
from datetime import date
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.employee import Employee
from app.models.client import Client
from app.models.service_type import ServiceType
from app.models.pay_period import PayPeriod
from app.models.timesheet import Timesheet
from app.models.time_entry import TimeEntry
from app.core.security import get_password_hash, create_access_token


@pytest.fixture
def _ctx():
    return {}


@pytest_asyncio.fixture(autouse=True)
async def seed_two_companies(db_session: AsyncSession, _ctx: dict):
    """Create two companies with their own data."""
    # Company A
    co_a = Company(name="Alpha Corp", slug="alpha-corp", is_active=True)
    co_b = Company(name="Beta Inc", slug="beta-inc", is_active=True)
    db_session.add_all([co_a, co_b])
    await db_session.flush()

    # Company A employees
    admin_a = Employee(
        company_id=co_a.id,
        email="admin-a@alpha.com", password_hash=get_password_hash("pass"),
        first_name="Alice", last_name="Admin",
        hire_date=date(2024, 1, 1), pay_period_group="A",
        is_admin=True, is_manager=True, is_active=True,
    )
    emp_a = Employee(
        company_id=co_a.id,
        email="emp-a@alpha.com", password_hash=get_password_hash("pass"),
        first_name="Amy", last_name="Employee",
        hire_date=date(2024, 1, 1), pay_period_group="A",
        is_active=True,
    )

    # Company B employees
    admin_b = Employee(
        company_id=co_b.id,
        email="admin-b@beta.com", password_hash=get_password_hash("pass"),
        first_name="Bob", last_name="Admin",
        hire_date=date(2024, 1, 1), pay_period_group="A",
        is_admin=True, is_manager=True, is_active=True,
    )
    emp_b = Employee(
        company_id=co_b.id,
        email="emp-b@beta.com", password_hash=get_password_hash("pass"),
        first_name="Bill", last_name="Employee",
        hire_date=date(2024, 1, 1), pay_period_group="A",
        is_active=True,
    )

    # Super admin (Company A, but can cross-company)
    super_admin = Employee(
        company_id=co_a.id,
        email="super@alpha.com", password_hash=get_password_hash("pass"),
        first_name="Super", last_name="Admin",
        hire_date=date(2024, 1, 1), pay_period_group="A",
        is_admin=True, is_super_admin=True, is_active=True,
    )

    db_session.add_all([admin_a, emp_a, admin_b, emp_b, super_admin])
    await db_session.flush()

    # Company A data
    client_a = Client(company_id=co_a.id, name="Alpha Client", industry="O&G", is_active=True)
    st_a = ServiceType(company_id=co_a.id, name="Alpha Service", is_billable=True, is_active=True)
    pp_a = PayPeriod(company_id=co_a.id, period_group="A", start_date=date(2026, 8, 3), end_date=date(2026, 8, 9), status="open")
    db_session.add_all([client_a, st_a, pp_a])
    await db_session.flush()

    ts_a = Timesheet(company_id=co_a.id, employee_id=emp_a.id, pay_period_id=pp_a.id, status="approved")
    db_session.add(ts_a)
    await db_session.flush()

    db_session.add(TimeEntry(
        timesheet_id=ts_a.id, work_date=date(2026, 8, 4),
        client_id=client_a.id, service_type_id=st_a.id,
        hours=8, work_mode="remote", is_overtime=False, is_billable=True,
    ))

    # Company B data
    client_b = Client(company_id=co_b.id, name="Beta Client", industry="Fiber", is_active=True)
    st_b = ServiceType(company_id=co_b.id, name="Beta Service", is_billable=True, is_active=True)
    pp_b = PayPeriod(company_id=co_b.id, period_group="A", start_date=date(2026, 8, 3), end_date=date(2026, 8, 9), status="open")
    db_session.add_all([client_b, st_b, pp_b])
    await db_session.flush()

    ts_b = Timesheet(company_id=co_b.id, employee_id=emp_b.id, pay_period_id=pp_b.id, status="approved")
    db_session.add(ts_b)
    await db_session.flush()

    db_session.add(TimeEntry(
        timesheet_id=ts_b.id, work_date=date(2026, 8, 4),
        client_id=client_b.id, service_type_id=st_b.id,
        hours=8, work_mode="remote", is_overtime=False, is_billable=True,
    ))

    await db_session.commit()

    def _headers(emp):
        token = create_access_token(data={"sub": str(emp.id), "email": emp.email})
        return {"Authorization": f"Bearer {token}"}

    _ctx.update({
        "co_a_id": str(co_a.id), "co_b_id": str(co_b.id),
        "admin_a": _headers(admin_a), "emp_a": _headers(emp_a),
        "admin_b": _headers(admin_b), "emp_b": _headers(emp_b),
        "super_admin": _headers(super_admin),
        "emp_a_id": str(emp_a.id), "emp_b_id": str(emp_b.id),
        "admin_a_id": str(admin_a.id), "admin_b_id": str(admin_b.id),
        "client_a_id": str(client_a.id), "client_b_id": str(client_b.id),
        "st_a_id": str(st_a.id), "st_b_id": str(st_b.id),
        "pp_a_id": str(pp_a.id), "pp_b_id": str(pp_b.id),
        "ts_a_id": str(ts_a.id), "ts_b_id": str(ts_b.id),
    })


# --- Employee isolation ---

@pytest.mark.asyncio
async def test_admin_a_cannot_list_company_b_employees(client: AsyncClient, _ctx: dict):
    resp = await client.get("/api/employees", headers=_ctx["admin_a"])
    assert resp.status_code == 200
    emails = [e["email"] for e in resp.json()]
    assert "emp-a@alpha.com" in emails
    assert "emp-b@beta.com" not in emails
    assert "admin-b@beta.com" not in emails


@pytest.mark.asyncio
async def test_admin_a_cannot_get_company_b_employee(client: AsyncClient, _ctx: dict):
    resp = await client.get(f"/api/employees/{_ctx['emp_b_id']}", headers=_ctx["admin_a"])
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_admin_a_cannot_update_company_b_employee(client: AsyncClient, _ctx: dict):
    resp = await client.patch(
        f"/api/employees/{_ctx['emp_b_id']}",
        json={"first_name": "Hacked"},
        headers=_ctx["admin_a"],
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_admin_a_cannot_delete_company_b_employee(client: AsyncClient, _ctx: dict):
    resp = await client.delete(f"/api/employees/{_ctx['emp_b_id']}", headers=_ctx["admin_a"])
    assert resp.status_code == 404


# --- Client isolation ---

@pytest.mark.asyncio
async def test_admin_a_cannot_list_company_b_clients(client: AsyncClient, _ctx: dict):
    resp = await client.get("/api/clients", headers=_ctx["admin_a"])
    assert resp.status_code == 200
    names = [c["name"] for c in resp.json()]
    assert "Alpha Client" in names
    assert "Beta Client" not in names


@pytest.mark.asyncio
async def test_admin_a_cannot_get_company_b_client(client: AsyncClient, _ctx: dict):
    resp = await client.get(f"/api/clients/{_ctx['client_b_id']}", headers=_ctx["admin_a"])
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_admin_a_cannot_update_company_b_client(client: AsyncClient, _ctx: dict):
    resp = await client.patch(
        f"/api/clients/{_ctx['client_b_id']}",
        json={"industry": "Hacked"},
        headers=_ctx["admin_a"],
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_admin_a_cannot_delete_company_b_client(client: AsyncClient, _ctx: dict):
    resp = await client.delete(f"/api/clients/{_ctx['client_b_id']}", headers=_ctx["admin_a"])
    assert resp.status_code == 404


# --- Service type isolation ---

@pytest.mark.asyncio
async def test_admin_a_cannot_list_company_b_service_types(client: AsyncClient, _ctx: dict):
    resp = await client.get("/api/service-types", headers=_ctx["admin_a"])
    assert resp.status_code == 200
    names = [s["name"] for s in resp.json()]
    assert "Alpha Service" in names
    assert "Beta Service" not in names


# --- Pay period isolation ---

@pytest.mark.asyncio
async def test_admin_a_cannot_get_company_b_pay_period(client: AsyncClient, _ctx: dict):
    resp = await client.get(f"/api/pay-periods/{_ctx['pp_b_id']}", headers=_ctx["admin_a"])
    assert resp.status_code == 404


# --- Timesheet isolation ---

@pytest.mark.asyncio
async def test_admin_a_cannot_get_company_b_timesheet(client: AsyncClient, _ctx: dict):
    resp = await client.get(f"/api/timesheets/{_ctx['ts_b_id']}", headers=_ctx["admin_a"])
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_admin_a_cannot_list_company_b_timesheets(client: AsyncClient, _ctx: dict):
    resp = await client.get("/api/timesheets", headers=_ctx["admin_a"])
    assert resp.status_code == 200
    ts_ids = [t["id"] for t in resp.json()]
    assert _ctx["ts_a_id"] in ts_ids
    assert _ctx["ts_b_id"] not in ts_ids


@pytest.mark.asyncio
async def test_admin_a_cannot_approve_company_b_timesheet(client: AsyncClient, _ctx: dict):
    resp = await client.post(
        f"/api/timesheets/{_ctx['ts_b_id']}/approve",
        headers=_ctx["admin_a"],
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_admin_a_cannot_reject_company_b_timesheet(client: AsyncClient, _ctx: dict):
    resp = await client.post(
        f"/api/timesheets/{_ctx['ts_b_id']}/reject",
        json={"rejection_reason": "hacked"},
        headers=_ctx["admin_a"],
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_admin_a_cannot_reopen_company_b_timesheet(client: AsyncClient, _ctx: dict):
    resp = await client.post(
        f"/api/timesheets/{_ctx['ts_b_id']}/reopen",
        headers=_ctx["admin_a"],
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_admin_a_cannot_delete_company_b_timesheet(client: AsyncClient, _ctx: dict):
    resp = await client.delete(
        f"/api/timesheets/{_ctx['ts_b_id']}",
        headers=_ctx["admin_a"],
    )
    assert resp.status_code == 404


# --- Report isolation ---

@pytest.mark.asyncio
async def test_reports_only_return_own_company_data(client: AsyncClient, _ctx: dict):
    """Manager from Company A only sees Company A data in payroll report."""
    resp = await client.get(
        "/api/reports/payroll",
        params={"format": "json", "pay_period_id": _ctx["pp_a_id"]},
        headers=_ctx["admin_a"],
    )
    assert resp.status_code == 200
    body = resp.json()
    for row in body["data"]:
        assert "Amy" in row["employee_name"] or "Alice" in row["employee_name"]
        assert "Bob" not in row["employee_name"]
        assert "Bill" not in row["employee_name"]


@pytest.mark.asyncio
async def test_reports_cannot_access_other_company_pay_period(client: AsyncClient, _ctx: dict):
    """Manager from Company A cannot pull report for Company B pay period."""
    resp = await client.get(
        "/api/reports/payroll",
        params={"format": "json", "pay_period_id": _ctx["pp_b_id"]},
        headers=_ctx["admin_a"],
    )
    # Either 404 (period not found) or 200 with empty data
    if resp.status_code == 200:
        assert len(resp.json()["data"]) == 0


# --- Password reset isolation ---

@pytest.mark.asyncio
async def test_admin_a_cannot_reset_company_b_password(client: AsyncClient, _ctx: dict):
    resp = await client.post(
        "/api/auth/admin-reset-password",
        json={"employee_id": _ctx["emp_b_id"], "new_password": "hacked123"},
        headers=_ctx["admin_a"],
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_admin_a_can_reset_own_company_password(client: AsyncClient, _ctx: dict):
    resp = await client.post(
        "/api/auth/admin-reset-password",
        json={"employee_id": _ctx["emp_a_id"], "new_password": "newpass123"},
        headers=_ctx["admin_a"],
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_super_admin_can_reset_any_company_password(client: AsyncClient, _ctx: dict):
    resp = await client.post(
        "/api/auth/admin-reset-password",
        json={"employee_id": _ctx["emp_b_id"], "new_password": "newpass123"},
        headers=_ctx["super_admin"],
    )
    assert resp.status_code == 200


# --- Company CRUD (super-admin only) ---

@pytest.mark.asyncio
async def test_regular_admin_cannot_list_companies(client: AsyncClient, _ctx: dict):
    resp = await client.get("/api/companies", headers=_ctx["admin_a"])
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_super_admin_can_list_companies(client: AsyncClient, _ctx: dict):
    resp = await client.get("/api/companies", headers=_ctx["super_admin"])
    assert resp.status_code == 200
    slugs = [c["slug"] for c in resp.json()]
    assert "alpha-corp" in slugs
    assert "beta-inc" in slugs


@pytest.mark.asyncio
async def test_super_admin_can_create_company(client: AsyncClient, _ctx: dict):
    resp = await client.post(
        "/api/companies",
        json={"name": "Gamma LLC", "slug": "gamma-llc"},
        headers=_ctx["super_admin"],
    )
    assert resp.status_code == 201
    assert resp.json()["slug"] == "gamma-llc"


@pytest.mark.asyncio
async def test_super_admin_can_update_company(client: AsyncClient, _ctx: dict):
    resp = await client.patch(
        f"/api/companies/{_ctx['co_b_id']}",
        json={"name": "Beta Corporation"},
        headers=_ctx["super_admin"],
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Beta Corporation"


@pytest.mark.asyncio
async def test_super_admin_can_soft_delete_company(client: AsyncClient, _ctx: dict):
    resp = await client.delete(
        f"/api/companies/{_ctx['co_b_id']}",
        headers=_ctx["super_admin"],
    )
    assert resp.status_code == 204

    # Should not appear in active-only list
    resp = await client.get("/api/companies", headers=_ctx["super_admin"])
    ids = [c["id"] for c in resp.json()]
    assert _ctx["co_b_id"] not in ids

    # Should appear in all companies list
    resp = await client.get("/api/companies?active_only=false", headers=_ctx["super_admin"])
    ids = [c["id"] for c in resp.json()]
    assert _ctx["co_b_id"] in ids
