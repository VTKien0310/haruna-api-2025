from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from app.database import DbSessionManager, PtoAffectEntryRecord, TimeOffEntryRecord
from tests.factories.database_records import TEST_USER_ID
from tests.fakes.sqlite_supabase import SqliteSupabasePort

FIRST_DAY = "2026-01-05"


async def test_post_time_off_rejects_a_missing_token(db_client: TestClient) -> None:
    response = db_client.post(
        "/api/attendance/time-offs",
        json={"start_date": FIRST_DAY, "type": 0},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["ok"] is False
    assert body["content"]["error"]["code"] == "unauthorized"


@pytest.mark.parametrize(
    ("requested_no_deduction", "expected_no_deduction"),
    [(None, 0), (0, 0), (1, 1)],
)
async def test_post_time_off_stores_a_range_and_affect_rows(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
    requested_no_deduction: int | None,
    expected_no_deduction: int,
) -> None:
    supabase.auth().register("token-1", user_id=TEST_USER_ID)
    payload: dict[str, str | int] = {
        "start_date": FIRST_DAY,
        "end_date": "2026-01-07",
        "type": 0,
    }
    if requested_no_deduction is not None:
        payload["no_deduction"] = requested_no_deduction

    response = db_client.post(
        "/api/attendance/time-offs",
        headers={"Authorization": "Bearer token-1"},
        json=payload,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    content = body["content"]
    assert [entry["date"] for entry in content] == [
        "2026-01-05",
        "2026-01-06",
        "2026-01-07",
    ]

    async with db_session_manager.session() as session:
        records = (await session.exec(select(TimeOffEntryRecord))).all()
        affect_rows = (await session.exec(select(PtoAffectEntryRecord))).all()

    assert len(records) == len(affect_rows) == 3
    assert {str(row.id) for row in records} == {entry["id"] for entry in content}
    assert {str(row.entry_id) for row in affect_rows} == {
        entry["id"] for entry in content
    }
    assert {str(row.owner_id) for row in affect_rows} == {TEST_USER_ID}
    assert {row.entry_type for row in affect_rows} == {"time_off_entries"}
    assert {row.no_deduction for row in affect_rows} == {expected_no_deduction}


async def test_post_time_off_reports_a_conflicting_shift(
    db_client: TestClient,
    supabase: SqliteSupabasePort,
) -> None:
    supabase.auth().register("token-1", user_id=TEST_USER_ID)
    headers = {"Authorization": "Bearer token-1"}
    db_client.post(
        "/api/attendance/time-offs",
        headers=headers,
        json={"start_date": FIRST_DAY, "type": 1},
    )

    response = db_client.post(
        "/api/attendance/time-offs",
        headers=headers,
        json={"start_date": FIRST_DAY, "type": 0},
    )

    assert response.status_code == 409
    body = response.json()
    assert body["ok"] is False
    assert body["content"]["error"]["code"] == "time_off_already_exists"
    assert FIRST_DAY in body["content"]["error"]["message"]


@pytest.mark.parametrize(
    "payload",
    [
        {"start_date": "2026-01-07", "end_date": "2026-01-06", "type": 0},
        {"start_date": FIRST_DAY, "end_date": "2026-01-06", "type": 1},
        {"start_date": FIRST_DAY, "end_date": "2027-01-06", "type": 0},
        {"start_date": FIRST_DAY, "type": 3},
        {"start_date": FIRST_DAY, "type": 0, "no_deduction": -1},
        {"start_date": FIRST_DAY, "type": 0, "no_deduction": 2},
    ],
)
async def test_post_time_off_rejects_invalid_fields(
    db_client: TestClient,
    supabase: SqliteSupabasePort,
    payload: dict[str, date | int | str],
) -> None:
    supabase.auth().register("token-1", user_id=TEST_USER_ID)

    response = db_client.post(
        "/api/attendance/time-offs",
        headers={"Authorization": "Bearer token-1"},
        json=payload,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["ok"] is False
    assert body["content"]["error"]["code"] == "validation_error"
