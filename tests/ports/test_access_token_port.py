import base64
import json
import time
from datetime import datetime, timezone

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from jwt.algorithms import ECAlgorithm, RSAAlgorithm

from app.core.config import settings
from app.ports.supabase import AccessTokenPort, VerifiedAccessToken
from app.ports.supabase.access_token_port import clear_jwks_cache

_ISSUER = "http://supabase.invalid/auth/v1"
_NOW = int(time.time())


@pytest.fixture(autouse=True)
def _empty_jwks_cache():
    clear_jwks_cache()
    yield
    clear_jwks_cache()


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


def _sign(private_key: object, algorithm: str, kid: str, **overrides: object) -> str:
    encoded = jwt.encode(
        _claims(**overrides),
        private_key,
        algorithm=algorithm,
        headers={"kid": kid},
    )
    assert isinstance(encoded, str)
    return encoded


def _transport(
    keys: list[dict[str, object]], calls: list[httpx.Request]
) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"keys": keys})

    return httpx.MockTransport(handler)


async def _verify(token: str, *, transport: httpx.MockTransport | None = None):
    if transport is None:

        def handler(request: httpx.Request) -> httpx.Response:
            raise AssertionError(request.url)

        transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        return await AccessTokenPort(http_client).verify(token)


async def test_es256_token_returns_the_subject_and_audience() -> None:
    private_key = _es256_key()
    issued_at = _NOW - 10
    calls: list[httpx.Request] = []
    verdict = await _verify(
        _sign(private_key, "ES256", "test-key", iat=issued_at),
        transport=_transport([_public_jwk(private_key, "test-key")], calls),
    )

    assert isinstance(verdict, VerifiedAccessToken)
    assert verdict.user_id == "user-1"
    assert verdict.audience == "authenticated"
    assert verdict.created_at == datetime.fromtimestamp(issued_at, tz=timezone.utc)
    assert len(calls) == 1
    assert str(calls[0].url) == f"{_ISSUER}/.well-known/jwks.json"
    assert calls[0].headers["apikey"] == settings.SUPABASE_SERVICE_ROLE_KEY


async def test_es256_created_at_claim_is_kept() -> None:
    private_key = _es256_key()
    verdict = await _verify(
        _sign(private_key, "ES256", "test-key", created_at="2020-05-01T12:30:00+00:00"),
        transport=_transport([_public_jwk(private_key, "test-key")], []),
    )

    assert isinstance(verdict, VerifiedAccessToken)
    assert verdict.created_at == datetime(2020, 5, 1, 12, 30, tzinfo=timezone.utc)


async def test_es256_keys_are_cached() -> None:
    private_key = _es256_key()
    calls: list[httpx.Request] = []
    transport = _transport([_public_jwk(private_key, "test-key")], calls)
    token = _sign(private_key, "ES256", "test-key")

    first = await _verify(token, transport=transport)
    second = await _verify(token, transport=transport)

    assert isinstance(first, VerifiedAccessToken)
    assert isinstance(second, VerifiedAccessToken)
    assert len(calls) == 1


async def test_rs256_token_is_accepted() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(RSAAlgorithm(RSAAlgorithm.SHA256).to_jwk(private_key.public_key()))
    assert isinstance(jwk, dict)
    jwk["kid"] = "rsa-key"
    jwk["alg"] = "RS256"
    jwk["use"] = "sig"

    verdict = await _verify(
        _sign(private_key, "RS256", "rsa-key"),
        transport=_transport([jwk], []),
    )

    assert isinstance(verdict, VerifiedAccessToken)
    assert verdict.user_id == "user-1"


async def test_hs256_token_is_rejected_without_fetching_jwks() -> None:
    encoded = jwt.encode(
        _claims(), "test-jwt-secret-for-unit-tests!!", algorithm="HS256"
    )
    assert isinstance(encoded, str)
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(500)

    verdict = await _verify(encoded, transport=httpx.MockTransport(handler))

    assert verdict is None
    assert calls == []


async def test_opaque_token_is_rejected() -> None:
    verdict = await _verify("token-1")

    assert verdict is None


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
async def test_es256_rejects_invalid_claims(overrides: dict[str, object]) -> None:
    private_key = _es256_key()
    verdict = await _verify(
        _sign(private_key, "ES256", "test-key", **overrides),
        transport=_transport([_public_jwk(private_key, "test-key")], []),
    )

    assert verdict is None


async def test_es256_rejects_a_bad_signature() -> None:
    private_key = _es256_key()
    verdict = await _verify(
        _sign(_es256_key(), "ES256", "test-key"),
        transport=_transport([_public_jwk(private_key, "test-key")], []),
    )

    assert verdict is None


async def test_none_algorithm_is_rejected() -> None:
    header = _b64({"alg": "none", "typ": "JWT"})
    payload = _b64(_claims())
    verdict = await _verify(f"{header}.{payload}.x")

    assert verdict is None


async def test_oversized_token_is_rejected() -> None:
    verdict = await _verify("a" * 20_000)

    assert verdict is None


async def test_unknown_kid_is_rejected_without_a_second_fetch() -> None:
    private_key = _es256_key()
    calls: list[httpx.Request] = []
    verdict = await _verify(
        _sign(private_key, "ES256", "test-key"),
        transport=_transport([_public_jwk(private_key, "other-key")], calls),
    )

    assert verdict is None
    assert len(calls) == 1


async def test_jwks_failure_is_rejected() -> None:
    private_key = _es256_key()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "unavailable"})

    verdict = await _verify(
        _sign(private_key, "ES256", "test-key"),
        transport=httpx.MockTransport(handler),
    )

    assert verdict is None


def _b64(value: object) -> str:
    raw = json.dumps(value, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
