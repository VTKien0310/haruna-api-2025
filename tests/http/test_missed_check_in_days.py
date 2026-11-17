from datetime import date

from fastapi.testclient import TestClient

from app.database import DbSessionManager
from tests.factories.database_records import TEST_USER_ID, make_profile_record
from tests.fakes.sqlite_supabase import SqliteSupabasePort


def test_get_missed_check_in_days_requires_authentication(
    db_client: TestClient,
) -> None:
    response = db_client.get("/api/attendance/missed-check-ins")

    assert response.status_code == 401
    body = response.json()
    assert body["ok"] is False
    assert body["content"]["error"]["code"] == "unauthorized"


async def test_get_missed_check_in_days_returns_the_current_year_list(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
) -> None:
    supabase.auth().register("token-1", user_id=TEST_USER_ID)
    async with db_session_manager.transaction() as session:
        session.add(make_profile_record(work_start_date=date.today()))

    response = db_client.get(
        "/api/attendance/missed-check-ins",
        headers={"Authorization": "Bearer token-1"},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "content": []}
