from datetime import date
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from app.database import DbSessionManager, PtoAffectEntryRecord, RemoteWorkEntryRecord
from tests.factories.database_records import TEST_USER_ID
from tests.fakes.sqlite_supabase import SqliteSupabasePort

DAY = "2026-01-05"


async def test_post_remote_work_rejects_a_missing_token(
    db_client: TestClient,
) -> None:
    response = db_client.post(
        "/api/attendance/remote-works",
        json={"date": DAY, "type": 0},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["ok"] is False
    assert body["content"]["error"]["code"] == "unauthorized"


async def test_post_remote_work_stores_entry_and_affect_row(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
) -> None:
    supabase.auth().register("token-1", user_id=TEST_USER_ID)

    response = db_client.post(
        "/api/attendance/remote-works",
        headers={"Authorization": "Bearer token-1"},
        json={"date": DAY, "type": 2},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    content = body["content"]
    assert content["date"] == DAY
    assert content["type"] == 2

    async with db_session_manager.session() as session:
        record = await session.get(RemoteWorkEntryRecord, UUID(content["id"]))
        affect_rows = (await session.exec(select(PtoAffectEntryRecord))).all()

    assert record is not None
    assert len(affect_rows) == 1
    assert str(affect_rows[0].owner_id) == TEST_USER_ID
    assert str(affect_rows[0].entry_id) == content["id"]
    assert affect_rows[0].entry_type == "remote_work_entries"
    assert affect_rows[0].no_deduction == 1


async def test_post_remote_work_reports_a_conflicting_shift(
    db_client: TestClient,
    supabase: SqliteSupabasePort,
) -> None:
    supabase.auth().register("token-1", user_id=TEST_USER_ID)
    headers = {"Authorization": "Bearer token-1"}
    db_client.post(
        "/api/attendance/remote-works",
        headers=headers,
        json={"date": DAY, "type": 1},
    )

    response = db_client.post(
        "/api/attendance/remote-works",
        headers=headers,
        json={"date": DAY, "type": 0},
    )

    assert response.status_code == 409
    body = response.json()
    assert body["ok"] is False
    assert body["content"]["error"]["code"] == "remote_work_already_exists"


async def test_remote_work_does_not_conflict_with_time_off(
    db_client: TestClient,
    supabase: SqliteSupabasePort,
) -> None:
    supabase.auth().register("token-1", user_id=TEST_USER_ID)
    headers = {"Authorization": "Bearer token-1"}
    time_off = db_client.post(
        "/api/attendance/time-offs",
        headers=headers,
        json={"start_date": DAY, "type": 0},
    )

    remote_work = db_client.post(
        "/api/attendance/remote-works",
        headers=headers,
        json={"date": DAY, "type": 0},
    )

    assert time_off.status_code == 200
    assert remote_work.status_code == 200


@pytest.mark.parametrize(
    "payload",
    [
        {"date": "not-a-date", "type": 0},
        {"date": DAY, "type": 3},
    ],
)
async def test_post_remote_work_rejects_invalid_date_or_type(
    db_client: TestClient,
    supabase: SqliteSupabasePort,
    payload: dict[str, date | int | str],
) -> None:
    supabase.auth().register("token-1", user_id=TEST_USER_ID)

    response = db_client.post(
        "/api/attendance/remote-works",
        headers={"Authorization": "Bearer token-1"},
        json=payload,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["ok"] is False
    assert body["content"]["error"]["code"] == "validation_error"
