from datetime import date, timedelta

import pytest

from app.models.pay_period import PayPeriod


@pytest.fixture
async def active_pay_period(db_session, test_user):
    today = date.today()
    pay_period = PayPeriod(
        period_group=test_user.pay_period_group,
        start_date=today - timedelta(days=7),
        end_date=today + timedelta(days=6),
        status="open",
    )
    db_session.add(pay_period)
    await db_session.commit()
    await db_session.refresh(pay_period)
    return pay_period


@pytest.mark.asyncio
async def test_create_time_entry_for_today(client, auth_headers, active_pay_period):
    current_ts_response = await client.get("/api/timesheets/current", headers=auth_headers)
    assert current_ts_response.status_code == 200
    timesheet_id = current_ts_response.json()["id"]

    response = await client.post(
        f"/api/timesheets/{timesheet_id}/entries",
        headers=auth_headers,
        json={
            "work_date": date.today().isoformat(),
            "work_mode": "remote",
            "hours": 8,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["work_date"] == date.today().isoformat()


@pytest.mark.asyncio
async def test_create_time_entry_for_past_day_in_pay_period(client, auth_headers, active_pay_period):
    current_ts_response = await client.get("/api/timesheets/current", headers=auth_headers)
    assert current_ts_response.status_code == 200
    timesheet_id = current_ts_response.json()["id"]

    past_work_date = (date.today() - timedelta(days=2)).isoformat()
    response = await client.post(
        f"/api/timesheets/{timesheet_id}/entries",
        headers=auth_headers,
        json={
            "work_date": past_work_date,
            "work_mode": "remote",
            "hours": 7.5,
        },
    )

    assert response.status_code == 201
    assert response.json()["work_date"] == past_work_date


@pytest.mark.asyncio
async def test_create_time_entry_outside_pay_period_fails(client, auth_headers, active_pay_period):
    current_ts_response = await client.get("/api/timesheets/current", headers=auth_headers)
    assert current_ts_response.status_code == 200
    timesheet_id = current_ts_response.json()["id"]

    outside_work_date = (active_pay_period.start_date - timedelta(days=1)).isoformat()
    response = await client.post(
        f"/api/timesheets/{timesheet_id}/entries",
        headers=auth_headers,
        json={
            "work_date": outside_work_date,
            "work_mode": "remote",
            "hours": 8,
        },
    )

    assert response.status_code == 400
    assert "within pay period" in response.json()["detail"]


@pytest.mark.asyncio
async def test_time_entry_mutations_blocked_when_submitted(client, auth_headers, active_pay_period):
    current_ts_response = await client.get("/api/timesheets/current", headers=auth_headers)
    assert current_ts_response.status_code == 200
    timesheet_id = current_ts_response.json()["id"]

    create_response = await client.post(
        f"/api/timesheets/{timesheet_id}/entries",
        headers=auth_headers,
        json={
            "work_date": date.today().isoformat(),
            "work_mode": "remote",
            "hours": 8,
        },
    )
    assert create_response.status_code == 201
    entry_id = create_response.json()["id"]

    submit_response = await client.post(
        f"/api/timesheets/{timesheet_id}/submit",
        headers=auth_headers,
    )
    assert submit_response.status_code == 200
    assert submit_response.json()["status"] == "submitted"

    create_after_submit = await client.post(
        f"/api/timesheets/{timesheet_id}/entries",
        headers=auth_headers,
        json={
            "work_date": date.today().isoformat(),
            "work_mode": "remote",
            "hours": 4,
        },
    )
    assert create_after_submit.status_code == 403

    update_after_submit = await client.patch(
        f"/api/timesheets/{timesheet_id}/entries/{entry_id}",
        headers=auth_headers,
        json={"hours": 6},
    )
    assert update_after_submit.status_code == 403

    delete_after_submit = await client.delete(
        f"/api/timesheets/{timesheet_id}/entries/{entry_id}",
        headers=auth_headers,
    )
    assert delete_after_submit.status_code == 403


@pytest.mark.asyncio
async def test_create_pto_entry_within_pay_period(client, auth_headers, active_pay_period):
    current_ts_response = await client.get("/api/timesheets/current", headers=auth_headers)
    assert current_ts_response.status_code == 200
    timesheet_id = current_ts_response.json()["id"]

    response = await client.post(
        f"/api/timesheets/{timesheet_id}/pto",
        headers=auth_headers,
        json={
            "pto_date": date.today().isoformat(),
            "pto_type": "personal",
            "hours": 8,
        },
    )

    assert response.status_code == 201
    assert response.json()["pto_date"] == date.today().isoformat()


@pytest.mark.asyncio
async def test_create_pto_entry_outside_pay_period_fails(client, auth_headers, active_pay_period):
    current_ts_response = await client.get("/api/timesheets/current", headers=auth_headers)
    assert current_ts_response.status_code == 200
    timesheet_id = current_ts_response.json()["id"]

    outside_date = (active_pay_period.start_date - timedelta(days=1)).isoformat()
    response = await client.post(
        f"/api/timesheets/{timesheet_id}/pto",
        headers=auth_headers,
        json={
            "pto_date": outside_date,
            "pto_type": "personal",
            "hours": 8,
        },
    )

    assert response.status_code == 400
    assert "within pay period" in response.json()["detail"]


@pytest.mark.asyncio
async def test_pto_mutations_blocked_when_submitted(client, auth_headers, active_pay_period):
    current_ts_response = await client.get("/api/timesheets/current", headers=auth_headers)
    assert current_ts_response.status_code == 200
    timesheet_id = current_ts_response.json()["id"]

    # Create a time entry so we can submit (need at least one entry)
    await client.post(
        f"/api/timesheets/{timesheet_id}/entries",
        headers=auth_headers,
        json={
            "work_date": date.today().isoformat(),
            "work_mode": "remote",
            "hours": 8,
        },
    )

    # Create a PTO entry before submitting
    pto_response = await client.post(
        f"/api/timesheets/{timesheet_id}/pto",
        headers=auth_headers,
        json={
            "pto_date": (date.today() - timedelta(days=1)).isoformat(),
            "pto_type": "sick",
            "hours": 4,
        },
    )
    assert pto_response.status_code == 201
    pto_id = pto_response.json()["id"]

    # Submit the timesheet
    submit_response = await client.post(
        f"/api/timesheets/{timesheet_id}/submit",
        headers=auth_headers,
    )
    assert submit_response.status_code == 200

    # Try to create PTO after submit
    create_after_submit = await client.post(
        f"/api/timesheets/{timesheet_id}/pto",
        headers=auth_headers,
        json={
            "pto_date": date.today().isoformat(),
            "pto_type": "personal",
            "hours": 8,
        },
    )
    assert create_after_submit.status_code == 400

    # Try to update PTO after submit
    update_after_submit = await client.patch(
        f"/api/timesheets/{timesheet_id}/pto/{pto_id}",
        headers=auth_headers,
        json={"hours": 6},
    )
    assert update_after_submit.status_code == 400

    # Try to delete PTO after submit
    delete_after_submit = await client.delete(
        f"/api/timesheets/{timesheet_id}/pto/{pto_id}",
        headers=auth_headers,
    )
    assert delete_after_submit.status_code == 400
