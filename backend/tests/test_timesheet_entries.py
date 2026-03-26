from datetime import date, timedelta

import pytest
import pytest_asyncio

from sqlalchemy import delete
from app.models.pay_period import PayPeriod
from app.models.client import Client
from app.models.location import Location
from app.models.job_code import JobCode


@pytest_asyncio.fixture
async def active_pay_period(db_session, test_user):
    today = date.today()
    start_date = today - timedelta(days=7)
    end_date = today + timedelta(days=6)

    # Avoid UNIQUE constraint failures when the DB is reused across tests.
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
    await db_session.flush()
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
            "description": "Test work",
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
            "description": "Past day work",
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
            "description": "Outside period",
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
            "description": "Test work",
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
            "description": "After submit",
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
            "description": "Test work",
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
    assert create_after_submit.status_code == 403

    # Try to update PTO after submit
    update_after_submit = await client.patch(
        f"/api/timesheets/{timesheet_id}/pto/{pto_id}",
        headers=auth_headers,
        json={"hours": 6},
    )
    assert update_after_submit.status_code == 403

    # Try to delete PTO after submit
    delete_after_submit = await client.delete(
        f"/api/timesheets/{timesheet_id}/pto/{pto_id}",
        headers=auth_headers,
    )
    assert delete_after_submit.status_code == 403


# --- Description and job code validation on create ---


@pytest.mark.asyncio
async def test_create_entry_without_description_fails(client, auth_headers, active_pay_period):
    ts = await client.get("/api/timesheets/current", headers=auth_headers)
    timesheet_id = ts.json()["id"]

    response = await client.post(
        f"/api/timesheets/{timesheet_id}/entries",
        headers=auth_headers,
        json={
            "work_date": date.today().isoformat(),
            "work_mode": "remote",
            "hours": 8,
        },
    )
    assert response.status_code == 400
    assert "Description is required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_entry_with_blank_description_fails(client, auth_headers, active_pay_period):
    ts = await client.get("/api/timesheets/current", headers=auth_headers)
    timesheet_id = ts.json()["id"]

    response = await client.post(
        f"/api/timesheets/{timesheet_id}/entries",
        headers=auth_headers,
        json={
            "work_date": date.today().isoformat(),
            "work_mode": "remote",
            "hours": 8,
            "description": "   ",
        },
    )
    assert response.status_code == 400
    assert "Description is required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_entry_requires_job_code_when_location_has_codes(
    client, auth_headers, active_pay_period, db_session, test_user
):
    ts = await client.get("/api/timesheets/current", headers=auth_headers)
    timesheet_id = ts.json()["id"]

    # Create client + location + job code
    await db_session.execute(delete(Client).where(Client.name == "JC Test Client"))
    test_client = Client(company_id=test_user.company_id, name="JC Test Client", is_active=True)
    db_session.add(test_client)
    await db_session.flush()

    location = Location(
        company_id=test_user.company_id, client_id=test_client.id,
        site_name="JC Test Site", is_active=True,
    )
    db_session.add(location)
    await db_session.flush()

    job_code = JobCode(
        company_id=test_user.company_id, location_id=location.id,
        code="JC-001", description="Test code", is_active=True,
    )
    db_session.add(job_code)
    await db_session.commit()
    await db_session.refresh(location)
    await db_session.refresh(job_code)

    # Missing job_code_id → 400
    response = await client.post(
        f"/api/timesheets/{timesheet_id}/entries",
        headers=auth_headers,
        json={
            "work_date": date.today().isoformat(),
            "work_mode": "remote",
            "hours": 8,
            "description": "Some work",
            "client_id": str(test_client.id),
            "location_id": str(location.id),
        },
    )
    assert response.status_code == 400
    assert "Site code is required" in response.json()["detail"]

    # With job_code_id → 201
    response = await client.post(
        f"/api/timesheets/{timesheet_id}/entries",
        headers=auth_headers,
        json={
            "work_date": date.today().isoformat(),
            "work_mode": "remote",
            "hours": 8,
            "description": "Some work",
            "client_id": str(test_client.id),
            "location_id": str(location.id),
            "job_code_id": str(job_code.id),
        },
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_entry_no_job_code_ok_when_location_has_no_codes(
    client, auth_headers, active_pay_period, db_session, test_user
):
    ts = await client.get("/api/timesheets/current", headers=auth_headers)
    timesheet_id = ts.json()["id"]

    # Create client + location with NO job codes
    await db_session.execute(delete(Client).where(Client.name == "No JC Client"))
    test_client = Client(company_id=test_user.company_id, name="No JC Client", is_active=True)
    db_session.add(test_client)
    await db_session.flush()

    location = Location(
        company_id=test_user.company_id, client_id=test_client.id,
        site_name="No JC Site", is_active=True,
    )
    db_session.add(location)
    await db_session.commit()
    await db_session.refresh(location)

    response = await client.post(
        f"/api/timesheets/{timesheet_id}/entries",
        headers=auth_headers,
        json={
            "work_date": date.today().isoformat(),
            "work_mode": "remote",
            "hours": 8,
            "description": "Work without job code",
            "client_id": str(test_client.id),
            "location_id": str(location.id),
        },
    )
    assert response.status_code == 201
