"""Tests for employee-detail and my-time-detail report endpoints."""

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
from app.core.security import get_password_hash, create_access_token


@pytest.fixture
def _setup_data():
    """Mutable dict populated by setup_report_data; shared across tests via indirect dep."""
    return {}


@pytest_asyncio.fixture(autouse=True)
async def setup_report_data(db_session: AsyncSession, _setup_data: dict):
    """Seed pay period, employees, timesheets, and entries for each test."""
    pp = PayPeriod(
        period_group="A",
        start_date=date(2026, 7, 5),
        end_date=date(2026, 7, 18),
        status="open",
    )
    db_session.add(pp)
    await db_session.flush()

    mgr = Employee(
        email="detail-mgr@test.com",
        password_hash=get_password_hash("pass"),
        first_name="Dana", last_name="Manager",
        hire_date=date(2024, 1, 1), pay_period_group="A",
        is_manager=True, is_active=True,
    )
    emp = Employee(
        email="detail-emp@test.com",
        password_hash=get_password_hash("pass"),
        first_name="Eve", last_name="Employee",
        hire_date=date(2024, 1, 1), pay_period_group="A",
        is_manager=False, is_active=True,
    )
    emp2 = Employee(
        email="detail-emp2@test.com",
        password_hash=get_password_hash("pass"),
        first_name="Frank", last_name="Worker",
        hire_date=date(2024, 1, 1), pay_period_group="A",
        is_manager=False, is_active=True,
    )
    db_session.add_all([mgr, emp, emp2])
    await db_session.flush()

    ts_draft = Timesheet(employee_id=emp.id, pay_period_id=pp.id, status="draft")
    db_session.add(ts_draft)
    await db_session.flush()

    db_session.add(TimeEntry(
        timesheet_id=ts_draft.id, work_date=date(2026, 7, 7),
        hours=8, work_mode="remote", is_overtime=False, is_billable=True,
    ))
    db_session.add(TimeEntry(
        timesheet_id=ts_draft.id, work_date=date(2026, 7, 8),
        hours=6, work_mode="on_site", is_overtime=False, is_billable=True,
    ))
    db_session.add(PTOEntry(
        timesheet_id=ts_draft.id, pto_date=date(2026, 7, 9),
        pto_type="personal", hours=8,
    ))

    ts_approved = Timesheet(employee_id=emp2.id, pay_period_id=pp.id, status="approved")
    db_session.add(ts_approved)
    await db_session.flush()

    db_session.add(TimeEntry(
        timesheet_id=ts_approved.id, work_date=date(2026, 7, 7),
        hours=10, work_mode="remote", is_overtime=True, is_billable=True,
    ))

    await db_session.commit()

    _setup_data.update({
        "mgr_headers": {"Authorization": f"Bearer {create_access_token(data={'sub': str(mgr.id), 'email': mgr.email})}"},
        "emp_headers": {"Authorization": f"Bearer {create_access_token(data={'sub': str(emp.id), 'email': emp.email})}"},
        "emp_id": str(emp.id),
        "emp2_id": str(emp2.id),
        "mgr_id": str(mgr.id),
    })


@pytest.mark.asyncio
async def test_manager_multi_employee(client: AsyncClient, _setup_data: dict):
    """Manager can get detail for two employees."""
    s = _setup_data
    resp = await client.get(
        "/api/reports/employee-detail",
        params={
            "start_date": "2026-07-05",
            "end_date": "2026-07-18",
            "employee_ids": f"{s['emp_id']},{s['emp2_id']}",
        },
        headers=s["mgr_headers"],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["report"] == "employee_detail"
    assert body["row_count"] == 4
    names = {r["employee_name"] for r in body["data"]}
    assert "Eve Employee" in names
    assert "Frank Worker" in names
    assert len(body["summary"]) == 2
    assert body["grand_total"]["total_hours"] == 32.0


@pytest.mark.asyncio
async def test_manager_status_filter(client: AsyncClient, _setup_data: dict):
    """Filtering by timesheet_status=draft excludes approved rows."""
    s = _setup_data
    resp = await client.get(
        "/api/reports/employee-detail",
        params={
            "start_date": "2026-07-05",
            "end_date": "2026-07-18",
            "employee_ids": f"{s['emp_id']},{s['emp2_id']}",
            "timesheet_status": "draft",
        },
        headers=s["mgr_headers"],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["row_count"] == 3
    for r in body["data"]:
        assert r["timesheet_status"] == "draft"


@pytest.mark.asyncio
async def test_employee_self_export(client: AsyncClient, _setup_data: dict):
    """Employee can download own data via my-time-detail."""
    s = _setup_data
    resp = await client.get(
        "/api/reports/my-time-detail",
        params={"start_date": "2026-07-05", "end_date": "2026-07-18"},
        headers=s["emp_headers"],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["row_count"] == 3
    for r in body["data"]:
        assert r["employee_name"] == "Eve Employee"


@pytest.mark.asyncio
async def test_employee_cannot_use_manager_endpoint(client: AsyncClient, _setup_data: dict):
    """Employee gets 403 on employee-detail (manager endpoint)."""
    s = _setup_data
    resp = await client.get(
        "/api/reports/employee-detail",
        params={
            "start_date": "2026-07-05",
            "end_date": "2026-07-18",
            "employee_id": s["emp_id"],
        },
        headers=s["emp_headers"],
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_date_range_validation(client: AsyncClient, _setup_data: dict):
    """start_date > end_date returns 400."""
    s = _setup_data
    resp = await client.get(
        "/api/reports/my-time-detail",
        params={"start_date": "2026-07-18", "end_date": "2026-07-05"},
        headers=s["emp_headers"],
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_empty_result(client: AsyncClient, _setup_data: dict):
    """No matching rows returns 200 with empty data and zeroed summary."""
    s = _setup_data
    resp = await client.get(
        "/api/reports/my-time-detail",
        params={"start_date": "2025-01-01", "end_date": "2025-01-31"},
        headers=s["emp_headers"],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["row_count"] == 0
    assert body["data"] == []
    assert body["grand_total"]["total_hours"] == 0


@pytest.mark.asyncio
async def test_csv_format(client: AsyncClient, _setup_data: dict):
    """CSV export works."""
    s = _setup_data
    resp = await client.get(
        "/api/reports/my-time-detail",
        params={
            "start_date": "2026-07-05",
            "end_date": "2026-07-18",
            "format": "csv",
        },
        headers=s["emp_headers"],
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "entry_kind" in resp.text
    assert "Eve Employee" in resp.text
