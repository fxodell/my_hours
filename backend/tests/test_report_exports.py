"""Integration tests for report export endpoints (CSV and Excel)."""

import pytest
import pytest_asyncio
from datetime import date
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pay_period import PayPeriod
from app.models.timesheet import Timesheet
from app.models.time_entry import TimeEntry
from app.models.pto_entry import PTOEntry
from app.models.employee import Employee
from app.models.client import Client
from app.models.service_type import ServiceType
from app.core.security import get_password_hash, create_access_token


@pytest.fixture
def _ctx():
    return {}


@pytest_asyncio.fixture(autouse=True)
async def seed(db_session: AsyncSession, _ctx: dict):
    pp = PayPeriod(
        period_group="A", start_date=date(2026, 5, 3),
        end_date=date(2026, 5, 9), status="open",
    )
    db_session.add(pp)
    await db_session.flush()

    mgr = Employee(
        email="export-mgr@test.com", password_hash=get_password_hash("pass"),
        first_name="Export", last_name="Manager",
        hire_date=date(2024, 1, 1), pay_period_group="A",
        is_manager=True, is_active=True,
    )
    emp = Employee(
        email="export-emp@test.com", password_hash=get_password_hash("pass"),
        first_name="Export", last_name="Employee",
        hire_date=date(2024, 1, 1), pay_period_group="A", is_active=True,
    )
    db_session.add_all([mgr, emp])
    await db_session.flush()

    cl = Client(name="Export Client", industry="O&G", is_active=True)
    st = ServiceType(name="Export Service", is_billable=True, is_active=True)
    db_session.add_all([cl, st])
    await db_session.flush()

    ts = Timesheet(employee_id=emp.id, pay_period_id=pp.id, status="approved")
    db_session.add(ts)
    await db_session.flush()

    db_session.add(TimeEntry(
        timesheet_id=ts.id, work_date=date(2026, 5, 5),
        client_id=cl.id, service_type_id=st.id,
        hours=8, work_mode="remote", is_overtime=False, is_billable=True,
    ))
    db_session.add(PTOEntry(
        timesheet_id=ts.id, pto_date=date(2026, 5, 6),
        pto_type="personal", hours=8,
    ))
    await db_session.commit()

    _ctx.update({
        "pp_id": str(pp.id),
        "emp_id": str(emp.id),
        "mgr_headers": {"Authorization": f"Bearer {create_access_token(data={'sub': str(mgr.id), 'email': mgr.email})}"},
        "emp_headers": {"Authorization": f"Bearer {create_access_token(data={'sub': str(emp.id), 'email': emp.email})}"},
    })


# --- Payroll Report ---

@pytest.mark.asyncio
async def test_payroll_csv(client: AsyncClient, _ctx: dict):
    resp = await client.get(
        "/api/reports/payroll",
        params={"format": "csv", "pay_period_id": _ctx["pp_id"]},
        headers=_ctx["mgr_headers"],
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "Export Employee" in resp.text


@pytest.mark.asyncio
async def test_payroll_json(client: AsyncClient, _ctx: dict):
    resp = await client.get(
        "/api/reports/payroll",
        params={"format": "json", "pay_period_id": _ctx["pp_id"]},
        headers=_ctx["mgr_headers"],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["report"] == "payroll"
    assert len(body["data"]) >= 1


@pytest.mark.asyncio
async def test_payroll_requires_manager(client: AsyncClient, _ctx: dict):
    resp = await client.get(
        "/api/reports/payroll",
        params={"format": "json"},
        headers=_ctx["emp_headers"],
    )
    assert resp.status_code == 403


# --- Billing Report ---

@pytest.mark.asyncio
async def test_billing_csv(client: AsyncClient, _ctx: dict):
    resp = await client.get(
        "/api/reports/billing",
        params={"format": "csv", "start_date": "2026-05-01", "end_date": "2026-05-31"},
        headers=_ctx["mgr_headers"],
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "Export Client" in resp.text


@pytest.mark.asyncio
async def test_billing_json(client: AsyncClient, _ctx: dict):
    resp = await client.get(
        "/api/reports/billing",
        params={"format": "json", "start_date": "2026-05-01", "end_date": "2026-05-31"},
        headers=_ctx["mgr_headers"],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["report"] == "billing"
    assert len(body["data"]) >= 1


# --- Hours by Employee ---

@pytest.mark.asyncio
async def test_hours_by_employee_csv(client: AsyncClient, _ctx: dict):
    resp = await client.get(
        "/api/reports/hours-by-employee",
        params={"format": "csv", "start_date": "2026-05-01", "end_date": "2026-05-31"},
        headers=_ctx["mgr_headers"],
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]


# --- Hours by Job Code ---

@pytest.mark.asyncio
async def test_hours_by_job_code_csv(client: AsyncClient, _ctx: dict):
    resp = await client.get(
        "/api/reports/hours-by-job-code",
        params={"format": "csv", "start_date": "2026-05-01", "end_date": "2026-05-31"},
        headers=_ctx["mgr_headers"],
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]


# --- Employee Detail Report ---

@pytest.mark.asyncio
async def test_employee_detail_csv(client: AsyncClient, _ctx: dict):
    resp = await client.get(
        "/api/reports/employee-detail",
        params={
            "start_date": "2026-05-01", "end_date": "2026-05-31",
            "employee_id": _ctx["emp_id"], "format": "csv",
        },
        headers=_ctx["mgr_headers"],
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "Export Employee" in resp.text


@pytest.mark.asyncio
async def test_employee_detail_excel(client: AsyncClient, _ctx: dict):
    resp = await client.get(
        "/api/reports/employee-detail",
        params={
            "start_date": "2026-05-01", "end_date": "2026-05-31",
            "employee_id": _ctx["emp_id"], "format": "excel",
        },
        headers=_ctx["mgr_headers"],
    )
    assert resp.status_code == 200
    assert "spreadsheetml" in resp.headers["content-type"]


# --- My Time Detail ---

@pytest.mark.asyncio
async def test_my_time_csv(client: AsyncClient, _ctx: dict):
    resp = await client.get(
        "/api/reports/my-time-detail",
        params={"start_date": "2026-05-01", "end_date": "2026-05-31", "format": "csv"},
        headers=_ctx["emp_headers"],
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "Export Employee" in resp.text


@pytest.mark.asyncio
async def test_my_time_excel(client: AsyncClient, _ctx: dict):
    resp = await client.get(
        "/api/reports/my-time-detail",
        params={"start_date": "2026-05-01", "end_date": "2026-05-31", "format": "excel"},
        headers=_ctx["emp_headers"],
    )
    assert resp.status_code == 200
    assert "spreadsheetml" in resp.headers["content-type"]


# --- Engage Export ---

@pytest.mark.asyncio
async def test_engage_export(client: AsyncClient, _ctx: dict):
    resp = await client.get(
        f"/api/reports/engage-export?pay_period_id={_ctx['pp_id']}",
        headers=_ctx["mgr_headers"],
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
