from datetime import date
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from app.database import DbSessionManager, LeaveWorkEntryRecord, PtoAffectEntryRecord
from tests.factories.database_records import TEST_USER_ID
from tests.fakes.sqlite_supabase import SqliteSupabasePort

DAY = "2026-01-05"


async def test_post_leave_work_rejects_a_missing_token(
    db_client: TestClient,
) -> None:
    response = db_client.post(
        "/api/attendance/leave-works",
        json={"date": DAY, "start": "09:00", "end": "10:00"},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["ok"] is False
    assert body["content"]["error"]["code"] == "unauthorized"


@pytest.mark.parametrize(
    ("requested_no_deduction", "expected_no_deduction"),
    [(None, 0), (0, 0), (1, 1)],
)
async def test_post_leave_work_drops_seconds_and_stores_affect_row(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
    requested_no_deduction: int | None,
    expected_no_deduction: int,
) -> None:
    supabase.auth().register("token-1", user_id=TEST_USER_ID)
    payload: dict[str, str | int] = {
        "date": DAY,
        "start": "09:00:59",
        "end": "10:00:59",
    }
    if requested_no_deduction is not None:
        payload["no_deduction"] = requested_no_deduction

    response = db_client.post(
        "/api/attendance/leave-works",
        headers={"Authorization": "Bearer token-1"},
        json=payload,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    content = body["content"]
    assert content["date"] == DAY
    assert content["start"] == "09:00:00"
    assert content["end"] == "10:00:00"

    async with db_session_manager.session() as session:
        record = await session.get(LeaveWorkEntryRecord, UUID(content["id"]))
        affect_rows = (await session.exec(select(PtoAffectEntryRecord))).all()

    assert record is not None
    assert len(affect_rows) == 1
    assert str(affect_rows[0].owner_id) == TEST_USER_ID
    assert str(affect_rows[0].entry_id) == content["id"]
    assert affect_rows[0].entry_type == "leave_work_entries"
    assert affect_rows[0].no_deduction == expected_no_deduction
    assert affect_rows[0].note == ""


@pytest.mark.parametrize(
    ("requested_note", "expected_note"),
    [(None, ""), ("clinic visit", "clinic visit")],
)
async def test_post_leave_work_stores_an_optional_affect_note(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
    requested_note: str | None,
    expected_note: str,
) -> None:
    supabase.auth().register("token-1", user_id=TEST_USER_ID)

    response = db_client.post(
        "/api/attendance/leave-works",
        headers={"Authorization": "Bearer token-1"},
        json={
            "date": DAY,
            "start": "09:00",
            "end": "10:00",
            "note": requested_note,
        },
    )

    assert response.status_code == 200
    async with db_session_manager.session() as session:
        affect_rows = (await session.exec(select(PtoAffectEntryRecord))).all()

    assert len(affect_rows) == 1
    assert affect_rows[0].note == expected_note


async def test_post_leave_work_reports_an_overlapping_interval(
    db_client: TestClient,
    supabase: SqliteSupabasePort,
) -> None:
    supabase.auth().register("token-1", user_id=TEST_USER_ID)
    headers = {"Authorization": "Bearer token-1"}
    db_client.post(
        "/api/attendance/leave-works",
        headers=headers,
        json={"date": DAY, "start": "10:00", "end": "11:00"},
    )

    response = db_client.post(
        "/api/attendance/leave-works",
        headers=headers,
        json={"date": DAY, "start": "10:30", "end": "11:30"},
    )

    assert response.status_code == 409
    body = response.json()
    assert body["ok"] is False
    assert body["content"]["error"]["code"] == "leave_work_overlaps"


async def test_post_leave_work_allows_touching_intervals(
    db_client: TestClient,
    supabase: SqliteSupabasePort,
) -> None:
    supabase.auth().register("token-1", user_id=TEST_USER_ID)
    headers = {"Authorization": "Bearer token-1"}
    first = db_client.post(
        "/api/attendance/leave-works",
        headers=headers,
        json={"date": DAY, "start": "10:00", "end": "11:00"},
    )
    second = db_client.post(
        "/api/attendance/leave-works",
        headers=headers,
        json={"date": DAY, "start": "11:00", "end": "12:00"},
    )

    assert first.status_code == second.status_code == 200


@pytest.mark.parametrize(
    "payload",
    [
        {"date": "not-a-date", "start": "09:00", "end": "10:00"},
        {"date": DAY, "start": "not-a-time", "end": "10:00"},
        {"date": DAY, "start": "10:00", "end": "10:00"},
        {"date": DAY, "start": "10:00:59", "end": "10:00:01"},
        {"date": DAY, "start": "09:00", "end": "10:00", "no_deduction": -1},
        {"date": DAY, "start": "09:00", "end": "10:00", "no_deduction": 2},
        {"date": DAY, "start": "09:00", "end": "10:00", "note": 1},
    ],
)
async def test_post_leave_work_rejects_invalid_fields(
    db_client: TestClient,
    supabase: SqliteSupabasePort,
    payload: dict[str, date | int | str],
) -> None:
    supabase.auth().register("token-1", user_id=TEST_USER_ID)

    response = db_client.post(
        "/api/attendance/leave-works",
        headers={"Authorization": "Bearer token-1"},
        json=payload,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["ok"] is False
    assert body["content"]["error"]["code"] == "validation_error"
