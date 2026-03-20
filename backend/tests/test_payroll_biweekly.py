"""Tests for the biweekly payroll rollup report."""

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
    """Mutable dict populated by setup_biweekly_data."""
    return {}


@pytest_asyncio.fixture(autouse=True)
async def setup_biweekly_data(db_session: AsyncSession, _setup_data: dict):
    """Seed pay periods, employees, timesheets, and entries for each test."""
    # Two consecutive Group A weekly periods: Sun-Sat
    pp1 = PayPeriod(
        period_group="A",
        start_date=date(2026, 6, 7),
        end_date=date(2026, 6, 13),
        status="open",
    )
    pp2 = PayPeriod(
        period_group="A",
        start_date=date(2026, 6, 14),
        end_date=date(2026, 6, 20),
        status="open",
    )
    pp_b = PayPeriod(
        period_group="B",
        start_date=date(2026, 6, 7),
        end_date=date(2026, 6, 13),
        status="open",
    )
    db_session.add_all([pp1, pp2, pp_b])
    await db_session.flush()

    emp_a = Employee(
        email="biweekly-a@test.com",
        password_hash=get_password_hash("pass"),
        first_name="Alice", last_name="Alpha",
        hire_date=date(2024, 1, 1), pay_period_group="A",
        is_manager=True, is_active=True,
    )
    emp_b = Employee(
        email="biweekly-b@test.com",
        password_hash=get_password_hash("pass"),
        first_name="Bob", last_name="Beta",
        hire_date=date(2024, 1, 1), pay_period_group="B",
        is_manager=True, is_active=True,
    )
    emp_reg = Employee(
        email="regular-biweekly@test.com",
        password_hash=get_password_hash("pass"),
        first_name="Regular", last_name="User",
        hire_date=date(2024, 1, 1), pay_period_group="A",
        is_manager=False, is_active=True,
    )
    db_session.add_all([emp_a, emp_b, emp_reg])
    await db_session.flush()

    ts1 = Timesheet(employee_id=emp_a.id, pay_period_id=pp1.id, status="approved")
    ts2 = Timesheet(employee_id=emp_a.id, pay_period_id=pp2.id, status="approved")
    ts_b = Timesheet(employee_id=emp_b.id, pay_period_id=pp_b.id, status="approved")
    db_session.add_all([ts1, ts2, ts_b])
    await db_session.flush()

    # Week 1: Mon 6/8 = 8h, Tue 6/9 = 6h + 2h OT
    db_session.add(TimeEntry(
        timesheet_id=ts1.id, work_date=date(2026, 6, 8),
        hours=8, work_mode="remote", is_overtime=False, is_billable=True,
    ))
    db_session.add(TimeEntry(
        timesheet_id=ts1.id, work_date=date(2026, 6, 9),
        hours=6, work_mode="remote", is_overtime=False, is_billable=True,
    ))
    db_session.add(TimeEntry(
        timesheet_id=ts1.id, work_date=date(2026, 6, 9),
        hours=2, work_mode="remote", is_overtime=True, is_billable=True,
    ))
    # Week 2: Mon 6/15 = 8h
    db_session.add(TimeEntry(
        timesheet_id=ts2.id, work_date=date(2026, 6, 15),
        hours=8, work_mode="remote", is_overtime=False, is_billable=True,
    ))
    # PTO: Fri 6/12 = 8h personal
    db_session.add(PTOEntry(
        timesheet_id=ts1.id, pto_date=date(2026, 6, 12),
        pto_type="personal", hours=8,
    ))

    await db_session.commit()

    _setup_data.update({
        "mgr_headers": {"Authorization": f"Bearer {create_access_token(data={'sub': str(emp_a.id), 'email': emp_a.email})}"},
        "reg_headers": {"Authorization": f"Bearer {create_access_token(data={'sub': str(emp_reg.id), 'email': emp_reg.email})}"},
    })


@pytest.mark.asyncio
async def test_biweekly_happy_path(client: AsyncClient, _setup_data: dict):
    """Two weeks, one Group A employee, daily cells reconcile with total."""
    resp = await client.get(
        "/api/reports/payroll-biweekly",
        params={
            "period_group": "A",
            "anchor_start_date": "2026-06-07",
            "format": "json",
        },
        headers=_setup_data["mgr_headers"],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["report"] == "payroll_biweekly"
    assert body["period_group"] == "A"
    assert body["biweekly_start"] == "2026-06-07"
    assert body["biweekly_end"] == "2026-06-20"

    data = body["data"]
    assert len(data) == 1
    row = data[0]
    assert row["employee_name"] == "Alice Alpha"
    assert row["weeks_count"] == 2
    assert row["missing_weeks"] == []

    hbd = row["hours_by_date"]
    assert hbd["2026-06-08"] == 8.0
    assert hbd["2026-06-09"] == 8.0
    assert hbd["2026-06-12"] == 8.0
    assert hbd["2026-06-15"] == 8.0
    assert hbd["2026-06-07"] == 0.0

    daily_sum = sum(hbd.values())
    assert row["period_total_hours"] == daily_sum
    assert row["period_total_hours"] == 32.0

    assert row["regular_hours"] == 22.0
    assert row["overtime_hours"] == 2.0
    assert row["total_work_hours"] == 24.0
    assert row["personal_pto_hours"] == 8.0
    assert row["total_pto_hours"] == 8.0
    assert row["total_hours"] == 32.0


@pytest.mark.asyncio
async def test_biweekly_invalid_group(client: AsyncClient, _setup_data: dict):
    resp = await client.get(
        "/api/reports/payroll-biweekly",
        params={"period_group": "X", "anchor_start_date": "2026-06-07"},
        headers=_setup_data["mgr_headers"],
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_biweekly_missing_period(client: AsyncClient, _setup_data: dict):
    """Anchor date that doesn't match any period."""
    resp = await client.get(
        "/api/reports/payroll-biweekly",
        params={"period_group": "A", "anchor_start_date": "2026-01-01"},
        headers=_setup_data["mgr_headers"],
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_biweekly_csv_format(client: AsyncClient, _setup_data: dict):
    """CSV export should have day columns and period_total_hours."""
    resp = await client.get(
        "/api/reports/payroll-biweekly",
        params={
            "period_group": "A",
            "anchor_start_date": "2026-06-07",
            "format": "csv",
        },
        headers=_setup_data["mgr_headers"],
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    content = resp.text
    assert "2026-06-07" in content
    assert "2026-06-20" in content
    assert "period_total_hours" in content


@pytest.mark.asyncio
async def test_biweekly_requires_manager(client: AsyncClient, _setup_data: dict):
    """Regular employees cannot access this report."""
    resp = await client.get(
        "/api/reports/payroll-biweekly",
        params={"period_group": "A", "anchor_start_date": "2026-06-07"},
        headers=_setup_data["reg_headers"],
    )
    assert resp.status_code == 403
