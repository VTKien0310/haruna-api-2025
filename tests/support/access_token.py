import json
import time

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from jwt.algorithms import ECAlgorithm

from app.core.config import settings
from tests.support.isolation import unexpected_interaction

_KID = "test-key"
_PRIVATE_KEY = ec.generate_private_key(ec.SECP256R1())


def access_token(user_id: str, **overrides: object) -> str:
    now = int(time.time())
    claims: dict[str, object] = {
        "sub": user_id,
        "aud": "authenticated",
        "role": "authenticated",
        "iss": _issuer(),
        "iat": now - 10,
        "exp": now + 3600,
    }
    claims.update(overrides)
    encoded = jwt.encode(claims, _PRIVATE_KEY, algorithm="ES256", headers={"kid": _KID})
    if not isinstance(encoded, str):
        raise RuntimeError("Test access token must be a string")
    return encoded


def jwks_http_client() -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if not request.url.path.endswith("/auth/v1/.well-known/jwks.json"):
            unexpected_interaction(f"HTTP {request.method} {request.url}")
        return httpx.Response(200, json={"keys": [_public_jwk()]})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _issuer() -> str:
    return f"{settings.SUPABASE_URL.strip().rstrip('/')}/auth/v1"


def _public_jwk() -> dict[str, object]:
    encoded = ECAlgorithm(ECAlgorithm.SHA256).to_jwk(_PRIVATE_KEY.public_key())
    jwk = json.loads(encoded)
    if not isinstance(jwk, dict):
        raise RuntimeError("Test JWKS key must be an object")
    jwk["kid"] = _KID
    jwk["alg"] = "ES256"
    jwk["use"] = "sig"
    return jwk
