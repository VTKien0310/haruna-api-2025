from datetime import date
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from app.database import DbSessionManager, PtoAffectEntryRecord
from tests.factories.database_records import (
    TEST_USER_ID,
    make_pto_bank_record,
    make_profile_record,
)
from tests.fakes.sqlite_supabase import SqliteSupabasePort

SUNDAY = "2026-01-04"
OTHER_USER_ID = str(uuid4())


async def _seed_user(db_session_manager: DbSessionManager) -> None:
    async with db_session_manager.transaction() as session:
        session.add(make_profile_record())
        session.add(
            make_pto_bank_record(
                year=date.today().year, annual_balance=0, seniority_balance=0
            )
        )


async def test_post_check_in_rejects_a_missing_token(db_client: TestClient) -> None:
    response = db_client.post(
        "/api/attendance/check-ins",
        json={"date": SUNDAY, "time": "09:00"},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["ok"] is False
    assert body["content"]["error"]["code"] == "unauthorized"


@pytest.mark.parametrize(
    ("requested_no_deduction", "expected_no_deduction"),
    [(None, 0), (0, 0), (1, 1)],
)
async def test_post_check_in_stores_the_arrival_and_the_affect_row(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
    requested_no_deduction: int | None,
    expected_no_deduction: int,
) -> None:
    supabase.auth().register("token-1", user_id=TEST_USER_ID)
    await _seed_user(db_session_manager)
    payload: dict[str, str | int] = {"date": SUNDAY, "time": "09:00:59"}
    if requested_no_deduction is not None:
        payload["no_deduction"] = requested_no_deduction

    response = db_client.post(
        "/api/attendance/check-ins",
        headers={"Authorization": "Bearer token-1"},
        json=payload,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    content = body["content"]
    assert content["date"] == SUNDAY
    assert content["time"] == "09:00:00"

    async with db_session_manager.session() as session:
        affect_rows = (await session.exec(select(PtoAffectEntryRecord))).all()

    assert len(affect_rows) == 1
    assert str(affect_rows[0].owner_id) == TEST_USER_ID
    assert str(affect_rows[0].entry_id) == content["id"]
    assert affect_rows[0].entry_type == "check_in_entries"
    assert affect_rows[0].no_deduction == expected_no_deduction
    assert affect_rows[0].note == ""


@pytest.mark.parametrize(
    ("requested_note", "expected_note"),
    [(None, ""), ("arrived after the train", "arrived after the train")],
)
async def test_post_check_in_stores_an_optional_affect_note(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
    requested_note: str | None,
    expected_note: str,
) -> None:
    supabase.auth().register("token-1", user_id=TEST_USER_ID)

    response = db_client.post(
        "/api/attendance/check-ins",
        headers={"Authorization": "Bearer token-1"},
        json={
            "date": SUNDAY,
            "time": "09:00",
            "note": requested_note,
            "no_deduction": 1,
        },
    )

    assert response.status_code == 200
    async with db_session_manager.session() as session:
        affect_rows = (await session.exec(select(PtoAffectEntryRecord))).all()

    assert len(affect_rows) == 1
    assert affect_rows[0].note == expected_note


async def test_post_check_in_reports_an_existing_arrival(
    db_client: TestClient,
    supabase: SqliteSupabasePort,
) -> None:
    supabase.auth().register("token-1", user_id=TEST_USER_ID)
    headers = {"Authorization": "Bearer token-1"}
    body = {"date": SUNDAY, "time": "09:00", "no_deduction": 1}
    db_client.post("/api/attendance/check-ins", headers=headers, json=body)

    response = db_client.post(
        "/api/attendance/check-ins",
        headers=headers,
        json={"date": SUNDAY, "time": "10:30"},
    )

    assert response.status_code == 409
    body = response.json()
    assert body["ok"] is False
    assert body["content"]["error"]["code"] == "check_in_already_exists"


async def test_post_check_in_allows_another_caller_on_the_same_date(
    db_client: TestClient,
    supabase: SqliteSupabasePort,
) -> None:
    supabase.auth().register("token-1", user_id=TEST_USER_ID)
    supabase.auth().register("token-2", user_id=OTHER_USER_ID)
    first = db_client.post(
        "/api/attendance/check-ins",
        headers={"Authorization": "Bearer token-1"},
        json={"date": SUNDAY, "time": "08:00"},
    )
    second = db_client.post(
        "/api/attendance/check-ins",
        headers={"Authorization": "Bearer token-2"},
        json={"date": SUNDAY, "time": "08:45", "no_deduction": 1},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["content"]["time"] == "08:45:00"


async def test_post_check_in_rejects_invalid_fields(
    db_client: TestClient,
    supabase: SqliteSupabasePort,
) -> None:
    supabase.auth().register("token-1", user_id=TEST_USER_ID)

    for payload in (
        {"date": "not-a-date", "time": "09:00"},
        {"date": SUNDAY, "time": "not-a-time"},
        {"date": SUNDAY, "time": "09:00", "no_deduction": -1},
        {"date": SUNDAY, "time": "09:00", "no_deduction": 2},
        {"date": SUNDAY, "time": "09:00", "note": 1},
    ):
        response = db_client.post(
            "/api/attendance/check-ins",
            headers={"Authorization": "Bearer token-1"},
            json=payload,
        )

        assert response.status_code == 422
        body = response.json()
        assert body["ok"] is False
        assert body["content"]["error"]["code"] == "validation_error"
