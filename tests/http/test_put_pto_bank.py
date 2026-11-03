import sqlite3
from datetime import date

from fastapi.testclient import TestClient

from tests.factories.records import insert_pto_bank, insert_profile
from tests.fakes.sqlite_supabase import SqliteSupabasePort


def test_put_pto_bank_rejects_a_missing_token(client: TestClient) -> None:
    response = client.put(f"/api/pto/banks/{date.today().year}")

    assert response.status_code == 401
    body = response.json()
    assert body["ok"] is False
    assert body["content"]["error"]["code"] == "unauthorized"


def test_put_pto_bank_creates_the_current_year_bank(
    client: TestClient, database: sqlite3.Connection, supabase: SqliteSupabasePort
) -> None:
    supabase.auth().register("token-1")
    insert_profile(database, user_id="user-1", work_start_date="2024-04-01")

    response = client.put(
        f"/api/pto/banks/{date.today().year}",
        headers={"Authorization": "Bearer token-1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    content = body["content"]
    assert content["owner_id"] == "user-1"
    assert content["year"] == date.today().year
    assert content["annual_balance"] == 13 * 480
    assert content["extended_balance"] == 0


def test_put_pto_bank_views_an_existing_past_year_record(
    client: TestClient, database: sqlite3.Connection, supabase: SqliteSupabasePort
) -> None:
    supabase.auth().register("token-1")
    insert_pto_bank(
        database,
        id="bank-past",
        owner_id="user-1",
        year=date.today().year - 1,
        annual_balance=100,
    )

    response = client.put(
        f"/api/pto/banks/{date.today().year - 1}",
        headers={"Authorization": "Bearer token-1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["content"]["id"] == "bank-past"
    assert body["content"]["annual_balance"] == 100


def test_put_pto_bank_reports_a_missing_past_year_record(
    client: TestClient, database: sqlite3.Connection, supabase: SqliteSupabasePort
) -> None:
    supabase.auth().register("token-1")
    insert_profile(database, user_id="user-1")

    response = client.put(
        f"/api/pto/banks/{date.today().year - 1}",
        headers={"Authorization": "Bearer token-1"},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["ok"] is False
    assert body["content"]["error"]["code"] == "pto_bank_not_found"
