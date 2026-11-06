from datetime import date

from fastapi.testclient import TestClient

from app.database import DbSessionManager
from tests.factories.database_records import (
    TEST_PTO_BANK_ID,
    TEST_USER_ID,
    make_profile_record,
    make_pto_bank_record,
)
from tests.fakes.sqlite_supabase import SqliteSupabasePort


async def test_put_pto_bank_rejects_a_missing_token(db_client: TestClient) -> None:
    response = db_client.put(f"/api/pto/banks/{date.today().year}")

    assert response.status_code == 401
    body = response.json()
    assert body["ok"] is False
    assert body["content"]["error"]["code"] == "unauthorized"


async def test_put_pto_bank_creates_the_current_year_bank(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
) -> None:
    supabase.auth().register("token-1", user_id=TEST_USER_ID)
    async with db_session_manager.transaction() as session:
        session.add(make_profile_record())

    response = db_client.put(
        f"/api/pto/banks/{date.today().year}",
        headers={"Authorization": "Bearer token-1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    content = body["content"]
    assert content["owner_id"] == TEST_USER_ID
    assert content["year"] == date.today().year
    assert content["annual_balance"] == 13 * 480
    assert content["extended_balance"] == 0


async def test_put_pto_bank_views_an_existing_past_year_record(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
) -> None:
    supabase.auth().register("token-1", user_id=TEST_USER_ID)
    async with db_session_manager.transaction() as session:
        session.add(
            make_pto_bank_record(
                id=TEST_PTO_BANK_ID,
                year=date.today().year - 1,
                annual_balance=100,
            )
        )

    response = db_client.put(
        f"/api/pto/banks/{date.today().year - 1}",
        headers={"Authorization": "Bearer token-1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["content"]["id"] == str(TEST_PTO_BANK_ID)
    assert body["content"]["annual_balance"] == 100


async def test_put_pto_bank_reports_a_missing_past_year_record(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
) -> None:
    supabase.auth().register("token-1", user_id=TEST_USER_ID)
    async with db_session_manager.transaction() as session:
        session.add(make_profile_record())

    response = db_client.put(
        f"/api/pto/banks/{date.today().year - 1}",
        headers={"Authorization": "Bearer token-1"},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["ok"] is False
    assert body["content"]["error"]["code"] == "pto_bank_not_found"
