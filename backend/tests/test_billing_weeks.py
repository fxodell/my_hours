from datetime import date

import pytest

from app.models.pay_period import PayPeriod


@pytest.mark.asyncio
async def test_billing_weeks_are_monday_sunday_pairs(
    client,
    db_session,
    test_user,
    auth_headers,
):
    pay_period = PayPeriod(
        company_id=test_user.company_id,
        period_group=test_user.pay_period_group,
        start_date=date(2026, 3, 2),   # Monday
        end_date=date(2026, 3, 15),    # Sunday
        status="open",
    )
    db_session.add(pay_period)
    await db_session.flush()

    create_resp = await client.post(
        "/api/timesheets",
        headers=auth_headers,
        json={
            "employee_id": str(test_user.id),
            "pay_period_id": str(pay_period.id),
        },
    )
    assert create_resp.status_code == 201
    timesheet_id = create_resp.json()["id"]

    weeks_resp = await client.get(
        f"/api/timesheets/{timesheet_id}/billing-weeks",
        headers=auth_headers,
    )
    assert weeks_resp.status_code == 200
    weeks = weeks_resp.json()
    assert len(weeks) == 2
    assert weeks[0]["week_start_date"] == "2026-03-02"
    assert weeks[0]["week_end_date"] == "2026-03-08"
    assert weeks[1]["week_start_date"] == "2026-03-09"
    assert weeks[1]["week_end_date"] == "2026-03-15"


@pytest.mark.asyncio
async def test_billed_billing_week_blocks_time_entry_mutations(
    client,
    db_session,
    test_user,
    auth_headers,
    manager_auth_headers,
):
    pay_period = PayPeriod(
        company_id=test_user.company_id,
        period_group=test_user.pay_period_group,
        start_date=date(2026, 3, 2),
        end_date=date(2026, 3, 15),
        status="open",
    )
    db_session.add(pay_period)
    await db_session.flush()

    create_resp = await client.post(
        "/api/timesheets",
        headers=auth_headers,
        json={
            "employee_id": str(test_user.id),
            "pay_period_id": str(pay_period.id),
        },
    )
    assert create_resp.status_code == 201
    timesheet_id = create_resp.json()["id"]

    entry_resp = await client.post(
        f"/api/timesheets/{timesheet_id}/entries",
        headers=auth_headers,
        json={
            "work_date": "2026-03-03",
            "work_mode": "remote",
            "hours": 8,
        },
    )
    assert entry_resp.status_code == 201
    entry_id = entry_resp.json()["id"]

    weeks_resp = await client.get(
        f"/api/timesheets/{timesheet_id}/billing-weeks",
        headers=auth_headers,
    )
    assert weeks_resp.status_code == 200
    week_id = weeks_resp.json()[0]["id"]

    submit_resp = await client.post(
        f"/api/timesheets/{timesheet_id}/billing-weeks/{week_id}/submit",
        headers=manager_auth_headers,
    )
    assert submit_resp.status_code == 200

    approve_resp = await client.post(
        f"/api/timesheets/{timesheet_id}/billing-weeks/{week_id}/approve",
        headers=manager_auth_headers,
    )
    assert approve_resp.status_code == 200

    billed_resp = await client.post(
        f"/api/timesheets/{timesheet_id}/billing-weeks/{week_id}/mark-billed",
        headers=manager_auth_headers,
    )
    assert billed_resp.status_code == 200
    assert billed_resp.json()["status"] == "billed"

    create_locked_resp = await client.post(
        f"/api/timesheets/{timesheet_id}/entries",
        headers=auth_headers,
        json={
            "work_date": "2026-03-04",
            "work_mode": "remote",
            "hours": 4,
        },
    )
    assert create_locked_resp.status_code == 403

    update_locked_resp = await client.patch(
        f"/api/timesheets/{timesheet_id}/entries/{entry_id}",
        headers=auth_headers,
        json={"hours": 7},
    )
    assert update_locked_resp.status_code == 403

    delete_locked_resp = await client.delete(
        f"/api/timesheets/{timesheet_id}/entries/{entry_id}",
        headers=auth_headers,
    )
    assert delete_locked_resp.status_code == 403
