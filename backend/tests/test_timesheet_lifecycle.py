"""Integration tests for timesheet submit/approve/reject/reopen lifecycle."""

import pytest
import pytest_asyncio
from datetime import date
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.pay_period import PayPeriod
from app.models.timesheet import Timesheet
from app.models.time_entry import TimeEntry
from app.models.employee import Employee
from app.core.security import get_password_hash, create_access_token


@pytest.fixture
def _ctx():
    return {}


@pytest_asyncio.fixture(autouse=True)
async def seed(db_session: AsyncSession, _ctx: dict):
    company = Company(name="Lifecycle Co", slug="lifecycle-co", is_active=True)
    db_session.add(company)
    await db_session.flush()

    pp = PayPeriod(
        company_id=company.id,
        period_group="A", start_date=date(2026, 4, 5),
        end_date=date(2026, 4, 11), status="open",
    )
    db_session.add(pp)
    await db_session.flush()

    emp = Employee(
        company_id=company.id,
        email="lifecycle-emp@test.com", password_hash=get_password_hash("pass"),
        first_name="Lifecycle", last_name="Employee",
        hire_date=date(2024, 1, 1), pay_period_group="A", is_active=True,
    )
    mgr = Employee(
        company_id=company.id,
        email="lifecycle-mgr@test.com", password_hash=get_password_hash("pass"),
        first_name="Lifecycle", last_name="Manager",
        hire_date=date(2024, 1, 1), pay_period_group="A",
        is_manager=True, is_active=True,
    )
    admin = Employee(
        company_id=company.id,
        email="lifecycle-admin@test.com", password_hash=get_password_hash("pass"),
        first_name="Lifecycle", last_name="Admin",
        hire_date=date(2024, 1, 1), pay_period_group="A",
        is_admin=True, is_active=True,
    )
    other = Employee(
        company_id=company.id,
        email="lifecycle-other@test.com", password_hash=get_password_hash("pass"),
        first_name="Other", last_name="Employee",
        hire_date=date(2024, 1, 1), pay_period_group="A", is_active=True,
    )
    db_session.add_all([emp, mgr, admin, other])
    await db_session.flush()

    ts = Timesheet(company_id=company.id, employee_id=emp.id, pay_period_id=pp.id, status="draft")
    empty_ts = Timesheet(company_id=company.id, employee_id=other.id, pay_period_id=pp.id, status="draft")
    db_session.add_all([ts, empty_ts])
    await db_session.flush()

    db_session.add(TimeEntry(
        timesheet_id=ts.id, work_date=date(2026, 4, 7),
        hours=8, work_mode="remote", is_overtime=False, is_billable=True,
    ))
    await db_session.commit()

    _ctx.update({
        "ts_id": str(ts.id),
        "emp_headers": {"Authorization": f"Bearer {create_access_token(data={'sub': str(emp.id), 'email': emp.email})}"},
        "mgr_headers": {"Authorization": f"Bearer {create_access_token(data={'sub': str(mgr.id), 'email': mgr.email})}"},
        "admin_headers": {"Authorization": f"Bearer {create_access_token(data={'sub': str(admin.id), 'email': admin.email})}"},
        "other_headers": {"Authorization": f"Bearer {create_access_token(data={'sub': str(other.id), 'email': other.email})}"},
        "empty_ts_id": str(empty_ts.id),
    })


# --- Submit ---

@pytest.mark.asyncio
async def test_submit_draft(client: AsyncClient, _ctx: dict):
    """Employee can submit a draft timesheet."""
    resp = await client.post(
        f"/api/timesheets/{_ctx['ts_id']}/submit",
        headers=_ctx["emp_headers"],
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "submitted"
    assert resp.json()["submitted_by"] is not None


@pytest.mark.asyncio
async def test_submit_not_owner(client: AsyncClient, _ctx: dict):
    """Another employee cannot submit someone else's timesheet."""
    resp = await client.post(
        f"/api/timesheets/{_ctx['ts_id']}/submit",
        headers=_ctx["other_headers"],
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_submit_on_behalf_manager(client: AsyncClient, _ctx: dict):
    """Manager can submit another employee timesheet."""
    resp = await client.post(
        f"/api/timesheets/{_ctx['ts_id']}/submit-on-behalf",
        headers=_ctx["mgr_headers"],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "submitted"
    assert body["submitted_by"] is not None


@pytest.mark.asyncio
async def test_submit_on_behalf_admin(client: AsyncClient, _ctx: dict):
    """Admin can submit another employee timesheet."""
    resp = await client.post(
        f"/api/timesheets/{_ctx['ts_id']}/submit-on-behalf",
        headers=_ctx["admin_headers"],
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "submitted"


@pytest.mark.asyncio
async def test_submit_on_behalf_requires_manager(client: AsyncClient, _ctx: dict):
    """Regular employee cannot submit on behalf."""
    resp = await client.post(
        f"/api/timesheets/{_ctx['ts_id']}/submit-on-behalf",
        headers=_ctx["other_headers"],
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_submit_on_behalf_empty_timesheet_fails(client: AsyncClient, _ctx: dict):
    """Cannot submit empty timesheet even when manager submits on behalf."""
    resp = await client.post(
        f"/api/timesheets/{_ctx['empty_ts_id']}/submit-on-behalf",
        headers=_ctx["mgr_headers"],
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_submit_already_submitted(client: AsyncClient, _ctx: dict, db_session: AsyncSession):
    """Cannot submit an already-submitted timesheet."""
    # First submit
    await client.post(f"/api/timesheets/{_ctx['ts_id']}/submit", headers=_ctx["emp_headers"])
    # Try again
    resp = await client.post(f"/api/timesheets/{_ctx['ts_id']}/submit", headers=_ctx["emp_headers"])
    assert resp.status_code == 400


# --- Approve ---

@pytest.mark.asyncio
async def test_approve_submitted(client: AsyncClient, _ctx: dict):
    """Manager can approve a submitted timesheet."""
    await client.post(f"/api/timesheets/{_ctx['ts_id']}/submit", headers=_ctx["emp_headers"])
    resp = await client.post(
        f"/api/timesheets/{_ctx['ts_id']}/approve",
        headers=_ctx["mgr_headers"],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "approved"
    assert body["approved_by"] is not None


@pytest.mark.asyncio
async def test_approve_draft_fails(client: AsyncClient, _ctx: dict):
    """Cannot approve a draft timesheet."""
    resp = await client.post(
        f"/api/timesheets/{_ctx['ts_id']}/approve",
        headers=_ctx["mgr_headers"],
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_approve_requires_manager(client: AsyncClient, _ctx: dict):
    """Regular employee cannot approve."""
    await client.post(f"/api/timesheets/{_ctx['ts_id']}/submit", headers=_ctx["emp_headers"])
    resp = await client.post(
        f"/api/timesheets/{_ctx['ts_id']}/approve",
        headers=_ctx["emp_headers"],
    )
    assert resp.status_code == 403


# --- Reject ---

@pytest.mark.asyncio
async def test_reject_submitted(client: AsyncClient, _ctx: dict):
    """Manager can reject a submitted timesheet with reason."""
    await client.post(f"/api/timesheets/{_ctx['ts_id']}/submit", headers=_ctx["emp_headers"])
    resp = await client.post(
        f"/api/timesheets/{_ctx['ts_id']}/reject",
        json={"rejection_reason": "Missing hours for Tuesday"},
        headers=_ctx["mgr_headers"],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "rejected"
    assert body["rejection_reason"] == "Missing hours for Tuesday"


@pytest.mark.asyncio
async def test_reject_draft_fails(client: AsyncClient, _ctx: dict):
    """Cannot reject a draft timesheet."""
    resp = await client.post(
        f"/api/timesheets/{_ctx['ts_id']}/reject",
        json={"rejection_reason": "test"},
        headers=_ctx["mgr_headers"],
    )
    assert resp.status_code == 400


# --- Reopen ---

@pytest.mark.asyncio
async def test_reopen_approved(client: AsyncClient, _ctx: dict):
    """Manager can reopen an approved timesheet back to draft."""
    await client.post(f"/api/timesheets/{_ctx['ts_id']}/submit", headers=_ctx["emp_headers"])
    await client.post(f"/api/timesheets/{_ctx['ts_id']}/approve", headers=_ctx["mgr_headers"])
    resp = await client.post(
        f"/api/timesheets/{_ctx['ts_id']}/reopen",
        headers=_ctx["mgr_headers"],
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "draft"
    assert body["submitted_at"] is None
    assert body["approved_at"] is None
    assert body["approved_by"] is None


@pytest.mark.asyncio
async def test_reopen_submitted(client: AsyncClient, _ctx: dict):
    """Manager can reopen a submitted timesheet."""
    await client.post(f"/api/timesheets/{_ctx['ts_id']}/submit", headers=_ctx["emp_headers"])
    resp = await client.post(
        f"/api/timesheets/{_ctx['ts_id']}/reopen",
        headers=_ctx["mgr_headers"],
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "draft"


@pytest.mark.asyncio
async def test_reopen_draft_fails(client: AsyncClient, _ctx: dict):
    """Cannot reopen a draft timesheet."""
    resp = await client.post(
        f"/api/timesheets/{_ctx['ts_id']}/reopen",
        headers=_ctx["mgr_headers"],
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_reopen_requires_manager(client: AsyncClient, _ctx: dict):
    """Regular employee cannot reopen."""
    await client.post(f"/api/timesheets/{_ctx['ts_id']}/submit", headers=_ctx["emp_headers"])
    resp = await client.post(
        f"/api/timesheets/{_ctx['ts_id']}/reopen",
        headers=_ctx["emp_headers"],
    )
    assert resp.status_code == 403


# --- Full lifecycle ---

@pytest.mark.asyncio
async def test_full_lifecycle(client: AsyncClient, _ctx: dict):
    """draft -> submit -> reject -> resubmit -> approve -> reopen -> draft."""
    ts_id = _ctx["ts_id"]
    emp = _ctx["emp_headers"]
    mgr = _ctx["mgr_headers"]

    # Submit
    r = await client.post(f"/api/timesheets/{ts_id}/submit", headers=emp)
    assert r.json()["status"] == "submitted"

    # Reject
    r = await client.post(
        f"/api/timesheets/{ts_id}/reject",
        json={"rejection_reason": "Fix hours"},
        headers=mgr,
    )
    assert r.json()["status"] == "rejected"

    # Resubmit (rejected -> submitted)
    r = await client.post(f"/api/timesheets/{ts_id}/submit", headers=emp)
    assert r.json()["status"] == "submitted"
    assert r.json()["rejection_reason"] is None

    # Approve
    r = await client.post(f"/api/timesheets/{ts_id}/approve", headers=mgr)
    assert r.json()["status"] == "approved"

    # Reopen
    r = await client.post(f"/api/timesheets/{ts_id}/reopen", headers=mgr)
    assert r.json()["status"] == "draft"
