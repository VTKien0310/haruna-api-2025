import base64
import json
import time
from datetime import datetime, timezone

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from jwt.algorithms import ECAlgorithm

from app.ports.supabase.access_token_verifier import (
    RejectedSupabaseAccessToken,
    UnresolvedSupabaseAccessToken,
    VerifiedSupabaseAccessToken,
    clear_supabase_jwks_cache,
    verify_supabase_access_token,
)

_SECRET = "test-jwt-secret-for-unit-tests!!"
_URL = "http://supabase.invalid"
_ISSUER = "http://supabase.invalid/auth/v1"
_NOW = int(time.time())


@pytest.fixture(autouse=True)
def _empty_jwks_cache():
    clear_supabase_jwks_cache()
    yield
    clear_supabase_jwks_cache()


def _claims(**overrides: object) -> dict[str, object]:
    claims: dict[str, object] = {
        "sub": "user-1",
        "aud": "authenticated",
        "role": "authenticated",
        "iss": _ISSUER,
        "iat": _NOW - 10,
        "exp": _NOW + 3600,
    }
    claims.update(overrides)
    return claims


def _hs256(secret: str = _SECRET, **overrides: object) -> str:
    encoded = jwt.encode(_claims(**overrides), secret, algorithm="HS256")
    assert isinstance(encoded, str)
    return encoded


def _es256_key() -> ec.EllipticCurvePrivateKey:
    return ec.generate_private_key(ec.SECP256R1())


def _public_jwk(private_key: ec.EllipticCurvePrivateKey, kid: str) -> dict[str, object]:
    encoded = ECAlgorithm(ECAlgorithm.SHA256).to_jwk(private_key.public_key())
    jwk = json.loads(encoded)
    assert isinstance(jwk, dict)
    jwk["kid"] = kid
    jwk["alg"] = "ES256"
    jwk["use"] = "sig"
    return jwk


def _es256(
    private_key: ec.EllipticCurvePrivateKey, kid: str, **overrides: object
) -> str:
    encoded = jwt.encode(
        _claims(**overrides),
        private_key,
        algorithm="ES256",
        headers={"kid": kid},
    )
    assert isinstance(encoded, str)
    return encoded


def _client(handler: httpx.MockTransport | None = None) -> httpx.AsyncClient:
    transport = handler or httpx.MockTransport(
        lambda request: httpx.Response(500, json={"error": "unexpected"})
    )
    return httpx.AsyncClient(transport=transport)


async def _verify(
    token: str,
    *,
    secret: str = "",
    transport: httpx.MockTransport | None = None,
    supabase_key: str = "service-role",
):
    async with _client(transport) as http_client:
        return await verify_supabase_access_token(
            token,
            http_client=http_client,
            supabase_url=_URL,
            jwt_secret=secret,
            supabase_key=supabase_key,
        )


async def test_hs256_token_returns_the_subject_and_audience() -> None:
    issued_at = _NOW - 10
    verdict = await _verify(_hs256(iat=issued_at), secret=_SECRET)

    assert isinstance(verdict, VerifiedSupabaseAccessToken)
    assert verdict.user_id == "user-1"
    assert verdict.audience == "authenticated"
    assert verdict.created_at == datetime.fromtimestamp(issued_at, tz=timezone.utc)


async def test_hs256_created_at_claim_is_kept() -> None:
    verdict = await _verify(
        _hs256(created_at="2020-05-01T12:30:00+00:00"),
        secret=_SECRET,
    )

    assert isinstance(verdict, VerifiedSupabaseAccessToken)
    assert verdict.created_at == datetime(2020, 5, 1, 12, 30, tzinfo=timezone.utc)


async def test_hs256_without_a_secret_is_left_for_the_auth_server() -> None:
    verdict = await _verify(_hs256(), secret="")

    assert isinstance(verdict, UnresolvedSupabaseAccessToken)


async def test_opaque_token_is_left_for_the_auth_server() -> None:
    verdict = await _verify("token-1", secret=_SECRET)

    assert isinstance(verdict, UnresolvedSupabaseAccessToken)


@pytest.mark.parametrize(
    "overrides",
    [
        {"exp": _NOW - 120},
        {"iss": "http://other.invalid/auth/v1"},
        {"aud": "anon"},
        {"role": "service_role"},
        {"sub": "   "},
    ],
)
async def test_hs256_rejects_invalid_claims(overrides: dict[str, object]) -> None:
    verdict = await _verify(_hs256(**overrides), secret=_SECRET)

    assert isinstance(verdict, RejectedSupabaseAccessToken)


async def test_hs256_rejects_a_bad_signature() -> None:
    verdict = await _verify(
        _hs256(secret="other-jwt-secret-for-unit-tests!"), secret=_SECRET
    )

    assert isinstance(verdict, RejectedSupabaseAccessToken)


async def test_none_algorithm_is_rejected() -> None:
    header = _b64({"alg": "none", "typ": "JWT"})
    payload = _b64(_claims())
    verdict = await _verify(f"{header}.{payload}.x", secret=_SECRET)

    assert isinstance(verdict, RejectedSupabaseAccessToken)


async def test_oversized_token_is_rejected() -> None:
    verdict = await _verify("a" * 20_000, secret=_SECRET)

    assert isinstance(verdict, RejectedSupabaseAccessToken)


async def test_es256_token_uses_jwks_and_caches_the_keys() -> None:
    private_key = _es256_key()
    jwk = _public_jwk(private_key, "test-key")
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"keys": [jwk]})

    transport = httpx.MockTransport(handler)
    token = _es256(private_key, "test-key")

    first = await _verify(token, transport=transport)
    second = await _verify(token, transport=transport)

    assert isinstance(first, VerifiedSupabaseAccessToken)
    assert first.user_id == "user-1"
    assert isinstance(second, VerifiedSupabaseAccessToken)
    assert len(calls) == 1
    assert str(calls[0].url) == f"{_ISSUER}/.well-known/jwks.json"
    assert calls[0].headers["apikey"] == "service-role"


async def test_es256_unknown_kid_is_rejected_without_a_second_fetch() -> None:
    private_key = _es256_key()
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(
            200, json={"keys": [_public_jwk(private_key, "other-key")]}
        )

    verdict = await _verify(
        _es256(private_key, "test-key"),
        transport=httpx.MockTransport(handler),
    )

    assert isinstance(verdict, RejectedSupabaseAccessToken)
    assert calls == [1]


async def test_jwks_failure_is_left_for_the_auth_server() -> None:
    private_key = _es256_key()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "unavailable"})

    verdict = await _verify(
        _es256(private_key, "test-key"),
        transport=httpx.MockTransport(handler),
    )

    assert isinstance(verdict, UnresolvedSupabaseAccessToken)


def _b64(value: object) -> str:
    raw = json.dumps(value, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
