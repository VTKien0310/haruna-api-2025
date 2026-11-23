import time
from datetime import date

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.database import DbSessionManager
from tests.factories.database_records import TEST_USER_ID, make_profile_record
from tests.fakes.sqlite_supabase import SqliteSupabasePort

_SECRET = "test-jwt-secret-for-unit-tests!!"


@pytest.fixture
def jwt_secret(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "SUPABASE_JWT_SECRET", _SECRET)


def _token(**overrides: object) -> str:
    now = int(time.time())
    claims: dict[str, object] = {
        "sub": TEST_USER_ID,
        "aud": "authenticated",
        "role": "authenticated",
        "iss": f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1",
        "iat": now - 10,
        "exp": now + 3600,
    }
    claims.update(overrides)
    encoded = jwt.encode(claims, _SECRET, algorithm="HS256")
    assert isinstance(encoded, str)
    return encoded


@pytest.mark.usefixtures("jwt_secret")
async def test_local_hs256_token_uses_the_subject_as_the_user_id(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
) -> None:
    async with db_session_manager.transaction() as session:
        session.add(make_profile_record())

    response = db_client.put(
        f"/api/pto/banks/{date.today().year}",
        headers={"Authorization": f"Bearer {_token()}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["content"]["owner_id"] == TEST_USER_ID


@pytest.mark.usefixtures("jwt_secret")
def test_expired_local_token_is_rejected_without_the_auth_server(
    client: TestClient,
    supabase: SqliteSupabasePort,
) -> None:
    token = _token(exp=int(time.time()) - 120)
    supabase.auth().register(token, user_id=TEST_USER_ID)

    response = client.post(
        "/api/medias/missing/thumbnails",
        json={"width": 8, "height": 8},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json()["content"]["error"]["code"] == "unauthorized"


def test_hs256_without_the_secret_falls_back_to_the_auth_server(
    client: TestClient, supabase: SqliteSupabasePort
) -> None:
    token = _token()
    supabase.auth().register(token, user_id=TEST_USER_ID)

    response = client.post(
        "/api/medias/missing/thumbnails",
        json={"width": 8, "height": 8},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.json()["content"]["error"]["code"] == "media_not_found"
