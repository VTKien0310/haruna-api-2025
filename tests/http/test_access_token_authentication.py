import time
from datetime import date

import jwt
from fastapi.testclient import TestClient

from app.core.config import settings
from app.database import DbSessionManager
from tests.factories.database_records import TEST_USER_ID, make_profile_record
from tests.support.access_token import access_token

_HS256_SECRET = "test-jwt-secret-for-unit-tests!!"


def _hs256(**overrides: object) -> str:
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
    encoded = jwt.encode(claims, _HS256_SECRET, algorithm="HS256")
    assert isinstance(encoded, str)
    return encoded


async def test_es256_token_uses_the_subject_as_the_user_id(
    jwks_db_client: TestClient, db_session_manager: DbSessionManager
) -> None:
    async with db_session_manager.transaction() as session:
        session.add(make_profile_record())

    response = jwks_db_client.put(
        f"/api/pto/banks/{date.today().year}",
        headers={"Authorization": f"Bearer {access_token(TEST_USER_ID)}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["content"]["owner_id"] == TEST_USER_ID


def test_hs256_token_is_rejected(jwks_client: TestClient) -> None:
    response = jwks_client.post(
        "/api/medias/missing/thumbnails",
        json={"width": 8, "height": 8},
        headers={"Authorization": f"Bearer {_hs256()}"},
    )

    assert response.status_code == 401
    assert response.json()["content"]["error"]["code"] == "unauthorized"


def test_expired_es256_token_is_rejected(jwks_client: TestClient) -> None:
    token = access_token(TEST_USER_ID, exp=int(time.time()) - 120)

    response = jwks_client.post(
        "/api/medias/missing/thumbnails",
        json={"width": 8, "height": 8},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json()["content"]["error"]["code"] == "unauthorized"


def test_opaque_token_is_rejected(jwks_client: TestClient) -> None:
    response = jwks_client.post(
        "/api/medias/missing/thumbnails",
        json={"width": 8, "height": 8},
        headers={"Authorization": "Bearer token-1"},
    )

    assert response.status_code == 401
    assert response.json()["content"]["error"]["code"] == "unauthorized"
