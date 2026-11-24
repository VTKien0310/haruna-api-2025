import logging
import time
from datetime import date

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.database import DbSessionManager
from app.ports.supabase import VerifiedAccessToken
from tests.factories.database_records import TEST_USER_ID, make_profile_record
from tests.fakes.access_token import AccessTokenFake
from tests.fakes.sqlite_supabase import SqliteSupabasePort
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


async def _fail_verification(
    _self: AccessTokenFake, _token: str
) -> VerifiedAccessToken | None:
    raise RuntimeError("access token verifier unavailable")


def _logged(caplog: logging.LogCaptureFixture) -> str:
    return " ".join(caplog.messages)


def test_verifier_exception_falls_back_to_supabase_auth(
    client: TestClient,
    supabase: SqliteSupabasePort,
    monkeypatch: pytest.MonkeyPatch,
    caplog: logging.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(AccessTokenFake, "verify", _fail_verification)
    supabase.auth().register("token-1", user_id=TEST_USER_ID)

    with caplog.at_level(logging.INFO, logger="app.auth"):
        response = client.post(
            "/api/medias/missing/thumbnails",
            json={"width": 8, "height": 8},
            headers={"Authorization": "Bearer token-1"},
        )

    assert response.status_code == 404
    assert response.json()["content"]["error"]["code"] == "media_not_found"
    logged = _logged(caplog)
    assert "reason=unexpected" in logged
    assert "error=RuntimeError: access token verifier unavailable" in logged
    assert "fallback=succeeded" in logged
    assert "path=fallback" in logged
    assert "token-1" not in logged


def test_supabase_auth_exception_during_fallback_is_logged_and_rejected(
    client: TestClient,
    supabase: SqliteSupabasePort,
    monkeypatch: pytest.MonkeyPatch,
    caplog: logging.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(AccessTokenFake, "verify", _fail_verification)

    def fail_get_user(_token: str) -> None:
        raise RuntimeError("Supabase Auth unavailable")

    monkeypatch.setattr(supabase.auth(), "get_user", fail_get_user)

    with caplog.at_level(logging.INFO, logger="app.auth"):
        response = client.post(
            "/api/medias/missing/thumbnails",
            json={"width": 8, "height": 8},
            headers={"Authorization": "Bearer token-1"},
        )

    assert response.status_code == 401
    assert response.json()["content"]["error"]["code"] == "unauthorized"
    logged = _logged(caplog)
    assert "reason=unexpected" in logged
    assert "error=RuntimeError: access token verifier unavailable" in logged
    assert "fallback=failed" in logged
    assert "fallback_error=RuntimeError: Supabase Auth unavailable" in logged
    assert "token-1" not in logged


async def test_es256_token_uses_the_subject_as_the_user_id(
    jwks_db_client: TestClient,
    db_session_manager: DbSessionManager,
    caplog: logging.LogCaptureFixture,
) -> None:
    async with db_session_manager.transaction() as session:
        session.add(make_profile_record())

    with caplog.at_level(logging.INFO, logger="app.auth"):
        response = jwks_db_client.put(
            f"/api/pto/banks/{date.today().year}",
            headers={"Authorization": f"Bearer {access_token(TEST_USER_ID)}"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["content"]["owner_id"] == TEST_USER_ID
    assert "path=local" in _logged(caplog)
    assert "fallback=" not in _logged(caplog)


def test_hs256_token_falls_back_to_supabase_auth(
    jwks_client: TestClient,
    supabase: SqliteSupabasePort,
    caplog: logging.LogCaptureFixture,
) -> None:
    token = _hs256()
    supabase.auth().register(token, user_id=TEST_USER_ID)

    with caplog.at_level(logging.INFO, logger="app.auth"):
        response = jwks_client.post(
            "/api/medias/missing/thumbnails",
            json={"width": 8, "height": 8},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 404
    assert response.json()["content"]["error"]["code"] == "media_not_found"
    logged = _logged(caplog)
    assert "reason=unsupported_algorithm" in logged
    assert "alg=HS256" in logged
    assert "fallback=succeeded" in logged
    assert "path=fallback" in logged
    assert token not in logged


def test_expired_es256_token_falls_back_to_supabase_auth(
    jwks_client: TestClient,
    supabase: SqliteSupabasePort,
    caplog: logging.LogCaptureFixture,
) -> None:
    token = access_token(TEST_USER_ID, exp=int(time.time()) - 120)
    supabase.auth().register(token, user_id=TEST_USER_ID)

    with caplog.at_level(logging.INFO, logger="app.auth"):
        response = jwks_client.post(
            "/api/medias/missing/thumbnails",
            json={"width": 8, "height": 8},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 404
    logged = _logged(caplog)
    assert "reason=jwt_rejected" in logged
    assert "fallback=succeeded" in logged
    assert token not in logged


def test_opaque_token_is_rejected_when_fallback_also_fails(
    jwks_client: TestClient,
    supabase: SqliteSupabasePort,
    caplog: logging.LogCaptureFixture,
) -> None:
    supabase.auth().reject("token-1")

    with caplog.at_level(logging.WARNING, logger="app.auth"):
        response = jwks_client.post(
            "/api/medias/missing/thumbnails",
            json={"width": 8, "height": 8},
            headers={"Authorization": "Bearer token-1"},
        )

    assert response.status_code == 401
    assert response.json()["content"]["error"]["code"] == "unauthorized"
    logged = _logged(caplog)
    assert "reason=malformed" in logged
    assert "fallback=failed" in logged
    assert "token-1" not in logged
