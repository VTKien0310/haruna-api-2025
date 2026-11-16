from datetime import date
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from app.database import DbSessionManager, PtoAffectEntryRecord, WorkTimeEntryRecord
from tests.factories.database_records import (
    TEST_USER_ID,
    make_pto_bank_record,
    make_profile_record,
)
from tests.fakes.sqlite_supabase import SqliteSupabasePort

DAY = "2026-01-05"


async def _seed_user(db_session_manager: DbSessionManager) -> None:
    async with db_session_manager.transaction() as session:
        session.add(make_profile_record())
        session.add(
            make_pto_bank_record(
                year=date.today().year, annual_balance=0, seniority_balance=0
            )
        )


async def test_post_work_time_rejects_a_missing_token(
    db_client: TestClient,
) -> None:
    response = db_client.post(
        "/api/attendance/work-times",
        json={"date": DAY, "time": 0, "type": 0, "duration": 60},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["ok"] is False
    assert body["content"]["error"]["code"] == "unauthorized"


@pytest.mark.parametrize(
    ("requested_no_deduction", "expected_no_deduction"),
    [(None, 0), (0, 0), (1, 1)],
)
async def test_post_work_time_stores_entry_and_affect_row(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
    requested_no_deduction: int | None,
    expected_no_deduction: int,
) -> None:
    supabase.auth().register("token-1", user_id=TEST_USER_ID)
    await _seed_user(db_session_manager)
    payload: dict[str, str | int] = {
        "date": DAY,
        "time": 1,
        "type": 0,
        "duration": 45,
    }
    if requested_no_deduction is not None:
        payload["no_deduction"] = requested_no_deduction

    response = db_client.post(
        "/api/attendance/work-times",
        headers={"Authorization": "Bearer token-1"},
        json=payload,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    content = body["content"]
    assert content["date"] == DAY
    assert content["time"] == 1
    assert content["type"] == 0
    assert content["duration"] == 45

    async with db_session_manager.session() as session:
        record = await session.get(WorkTimeEntryRecord, UUID(content["id"]))
        affect_rows = (await session.exec(select(PtoAffectEntryRecord))).all()

    assert record is not None
    assert record.time == 1
    assert record.type == 0
    assert record.duration == 45
    assert len(affect_rows) == 1
    assert str(affect_rows[0].owner_id) == TEST_USER_ID
    assert str(affect_rows[0].entry_id) == content["id"]
    assert affect_rows[0].entry_type == "work_time_entries"
    assert affect_rows[0].no_deduction == expected_no_deduction
    assert affect_rows[0].note == ""


@pytest.mark.parametrize(
    ("requested_note", "expected_note"),
    [(None, ""), ("left for the school run", "left for the school run")],
)
async def test_post_work_time_stores_an_optional_affect_note(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
    requested_note: str | None,
    expected_note: str,
) -> None:
    supabase.auth().register("token-1", user_id=TEST_USER_ID)

    response = db_client.post(
        "/api/attendance/work-times",
        headers={"Authorization": "Bearer token-1"},
        json={
            "date": DAY,
            "time": 0,
            "type": 0,
            "duration": 30,
            "note": requested_note,
            "no_deduction": 1,
        },
    )

    assert response.status_code == 200
    async with db_session_manager.session() as session:
        affect_rows = (await session.exec(select(PtoAffectEntryRecord))).all()

    assert len(affect_rows) == 1
    assert affect_rows[0].note == expected_note


async def test_post_work_time_rejects_the_same_type_in_the_same_shift(
    db_client: TestClient,
    supabase: SqliteSupabasePort,
) -> None:
    supabase.auth().register("token-1", user_id=TEST_USER_ID)
    headers = {"Authorization": "Bearer token-1"}
    payload = {"date": DAY, "time": 0, "type": 0, "duration": 60, "no_deduction": 1}
    db_client.post("/api/attendance/work-times", headers=headers, json=payload)

    response = db_client.post(
        "/api/attendance/work-times", headers=headers, json=payload
    )

    assert response.status_code == 409
    body = response.json()
    assert body["ok"] is False
    assert body["content"]["error"]["code"] == "work_time_already_exists"


async def test_post_work_time_rejects_durations_covering_the_shift(
    db_client: TestClient,
    supabase: SqliteSupabasePort,
) -> None:
    supabase.auth().register("token-1", user_id=TEST_USER_ID)
    headers = {"Authorization": "Bearer token-1"}
    db_client.post(
        "/api/attendance/work-times",
        headers=headers,
        json={"date": DAY, "time": 0, "type": 0, "duration": 200, "no_deduction": 1},
    )

    response = db_client.post(
        "/api/attendance/work-times",
        headers=headers,
        json={"date": DAY, "time": 0, "type": 1, "duration": 40},
    )

    assert response.status_code == 409
    body = response.json()
    assert body["content"]["error"]["code"] == "work_time_overlaps"


async def test_same_work_time_type_in_different_shifts_is_allowed(
    db_client: TestClient,
    supabase: SqliteSupabasePort,
) -> None:
    supabase.auth().register("token-1", user_id=TEST_USER_ID)
    headers = {"Authorization": "Bearer token-1"}

    morning = db_client.post(
        "/api/attendance/work-times",
        headers=headers,
        json={"date": DAY, "time": 0, "type": 0, "duration": 60, "no_deduction": 1},
    )
    afternoon = db_client.post(
        "/api/attendance/work-times",
        headers=headers,
        json={"date": DAY, "time": 1, "type": 0, "duration": 60, "no_deduction": 1},
    )

    assert morning.status_code == afternoon.status_code == 200


@pytest.mark.parametrize(
    "payload",
    [
        {"date": "not-a-date", "time": 0, "type": 0, "duration": 60},
        {"date": DAY, "time": 2, "type": 0, "duration": 60},
        {"date": DAY, "time": 0, "type": 2, "duration": 60},
        {"date": DAY, "time": 0, "type": 0, "duration": 0},
        {"date": DAY, "time": 0, "type": 0, "duration": 241},
        {"date": DAY, "time": 0, "type": 0, "duration": 60, "no_deduction": -1},
        {"date": DAY, "time": 0, "type": 0, "duration": 60, "no_deduction": 2},
        {"date": DAY, "time": 0, "type": 0, "duration": 60, "note": 1},
    ],
)
async def test_post_work_time_rejects_invalid_fields(
    db_client: TestClient,
    supabase: SqliteSupabasePort,
    payload: dict[str, date | int | str],
) -> None:
    supabase.auth().register("token-1", user_id=TEST_USER_ID)

    response = db_client.post(
        "/api/attendance/work-times",
        headers={"Authorization": "Bearer token-1"},
        json=payload,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["ok"] is False
    assert body["content"]["error"]["code"] == "validation_error"
