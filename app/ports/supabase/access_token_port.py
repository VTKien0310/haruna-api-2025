import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated

import httpx
import jwt
from fastapi import Depends
from jwt import PyJWK, PyJWTError

from app.core import BasicHttpClientDep, settings

_ASYMMETRIC_ALGORITHMS = frozenset({"ES256", "RS256"})
_AUTHENTICATED = "authenticated"
_JWKS_TTL_SECONDS = 60 * 60
_JWKS_REFRESH_AFTER_SECONDS = 60
_MAX_TOKEN_LENGTH = 16_384
_CLOCK_LEEWAY_SECONDS = 10

_AMBIGUOUS_KEY = object()
_INVALID_KEY = object()

_jwks_cache: dict[str, tuple[float, float, list[dict[str, object]]]] = {}
_jwks_lock: asyncio.Lock | None = None
_jwks_lock_loop: asyncio.AbstractEventLoop | None = None


@dataclass(frozen=True)
class VerifiedAccessToken:
    user_id: str
    audience: str
    created_at: datetime


class AccessTokenPort:
    def __init__(self, http_client: BasicHttpClientDep) -> None:
        self.__http_client = http_client
        self.__supabase_url = settings.SUPABASE_URL
        self.__supabase_key = settings.SUPABASE_SERVICE_ROLE_KEY

    async def verify(self, token: str) -> VerifiedAccessToken | None:
        if len(token) > _MAX_TOKEN_LENGTH or token.count(".") != 2:
            return None
        if any(part == "" for part in token.split(".")):
            return None

        issuer = _issuer(self.__supabase_url)
        if issuer is None:
            return None

        try:
            header = jwt.get_unverified_header(token)
        except PyJWTError:
            return None

        algorithm = header.get("alg")
        if not isinstance(algorithm, str) or algorithm not in _ASYMMETRIC_ALGORITHMS:
            return None

        kid = header.get("kid")
        key_id = kid if isinstance(kid, str) and kid else None
        jwks_url = f"{issuer}/.well-known/jwks.json"
        loaded = await _load_jwks(
            jwks_url, self.__http_client, self.__supabase_key, force=False
        )
        if loaded is None:
            return None
        keys, fetched_at = loaded

        signing_key = _signing_key_for_token(keys, kid=key_id, algorithm=algorithm)
        if signing_key is _AMBIGUOUS_KEY or signing_key is _INVALID_KEY:
            return None
        if (
            signing_key is None
            and (time.monotonic() - fetched_at) > _JWKS_REFRESH_AFTER_SECONDS
        ):
            loaded = await _load_jwks(
                jwks_url, self.__http_client, self.__supabase_key, force=True
            )
            if loaded is None:
                return None
            keys, _fetched_at = loaded
            signing_key = _signing_key_for_token(keys, kid=key_id, algorithm=algorithm)

        if not _is_signing_key(signing_key):
            return None

        return _identity_from_token(token, signing_key, [algorithm], issuer)


def clear_jwks_cache() -> None:
    _jwks_cache.clear()


AccessTokenPortDep = Annotated[AccessTokenPort, Depends()]


def _issuer(supabase_url: str) -> str | None:
    base = supabase_url.strip().rstrip("/")
    if not base:
        return None
    return f"{base}/auth/v1"


def _is_signing_key(signing_key: object | None) -> bool:
    return (
        signing_key is not None
        and signing_key is not _AMBIGUOUS_KEY
        and signing_key is not _INVALID_KEY
    )


def _identity_from_token(
    token: str,
    key: object,
    algorithms: list[str],
    issuer: str,
) -> VerifiedAccessToken | None:
    try:
        decoded = jwt.decode(
            token,
            key,
            algorithms=algorithms,
            audience=_AUTHENTICATED,
            issuer=issuer,
            leeway=_CLOCK_LEEWAY_SECONDS,
            options={"require": ["exp", "iat", "sub", "aud", "iss"]},
        )
    except PyJWTError:
        return None

    if not isinstance(decoded, dict) or decoded.get("role") != _AUTHENTICATED:
        return None

    subject = decoded.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        return None

    audience = _audience(decoded.get("aud"))
    if audience is None:
        return None

    issued_at = _unix_time(decoded.get("iat"))
    if issued_at is None:
        return None

    return VerifiedAccessToken(
        user_id=subject,
        audience=audience,
        created_at=_created_at(decoded.get("created_at"), issued_at),
    )


def _audience(value: object) -> str | None:
    if value == _AUTHENTICATED:
        return _AUTHENTICATED
    if isinstance(value, list) and _AUTHENTICATED in value:
        return _AUTHENTICATED
    return None


def _created_at(value: object, issued_at: int) -> datetime:
    # A standard Supabase access token has no account created_at claim.
    # Callers identify the user by sub. iat keeps the field a real timestamp.
    if isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            parsed = None
        if parsed is not None:
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed
    return datetime.fromtimestamp(issued_at, tz=timezone.utc)


def _unix_time(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value)


def _signing_key_for_token(
    keys: list[dict[str, object]], *, kid: str | None, algorithm: str
) -> object | None:
    chosen: dict[str, object] | None = None
    for item in keys:
        if item.get("use") not in (None, "sig"):
            continue
        item_algorithm = item.get("alg")
        if isinstance(item_algorithm, str) and item_algorithm != algorithm:
            continue
        item_kid = item.get("kid")
        if kid is not None and item_kid != kid:
            continue
        if chosen is not None:
            return _AMBIGUOUS_KEY
        chosen = item
    if chosen is None:
        return None
    try:
        return PyJWK.from_dict(chosen).key
    except PyJWTError, ValueError, TypeError:
        return _INVALID_KEY


async def _load_jwks(
    url: str,
    http_client: httpx.AsyncClient,
    supabase_key: str,
    *,
    force: bool,
) -> tuple[list[dict[str, object]], float] | None:
    now = time.monotonic()
    if not force:
        cached = _read_cache(url, now)
        if cached is not None:
            return cached

    async with _lock_for_running_loop():
        if not force:
            cached = _read_cache(url, time.monotonic())
            if cached is not None:
                return cached
        try:
            response = await http_client.get(url, headers=_jwks_headers(supabase_key))
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError, ValueError:
            return None

        keys = _jwks_keys(payload)
        if not keys:
            return None
        fetched_at = time.monotonic()
        _jwks_cache[url] = (fetched_at + _JWKS_TTL_SECONDS, fetched_at, keys)
        return keys, fetched_at


def _read_cache(url: str, now: float) -> tuple[list[dict[str, object]], float] | None:
    cached = _jwks_cache.get(url)
    if cached is None or cached[0] <= now:
        return None
    return cached[2], cached[1]


def _jwks_keys(payload: object) -> list[dict[str, object]]:
    if not isinstance(payload, dict):
        return []
    keys = payload.get("keys")
    if not isinstance(keys, list):
        return []
    return [key for key in keys if isinstance(key, dict)]


def _jwks_headers(api_key: str) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    stripped = api_key.strip()
    if stripped:
        headers["apikey"] = stripped
    return headers


def _lock_for_running_loop() -> asyncio.Lock:
    global _jwks_lock, _jwks_lock_loop
    loop = asyncio.get_running_loop()
    if _jwks_lock is None or _jwks_lock_loop is not loop:
        _jwks_lock = asyncio.Lock()
        _jwks_lock_loop = loop
    return _jwks_lock
