import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated, ClassVar

import httpx
import jwt
from fastapi import Depends
from jwt import PyJWK, PyJWTError

from app.core import BasicHttpClientDep, settings


@dataclass(frozen=True)
class VerifiedAccessToken:
    user_id: str
    audience: str
    created_at: datetime


class AccessTokenPort:
    __ASYMMETRIC_ALGORITHMS: ClassVar[frozenset[str]] = frozenset({"ES256", "RS256"})
    __AUTHENTICATED: ClassVar[str] = "authenticated"
    __JWKS_TTL_SECONDS: ClassVar[int] = 60 * 60
    __JWKS_REFRESH_AFTER_SECONDS: ClassVar[int] = 60
    __MAX_TOKEN_LENGTH: ClassVar[int] = 16_384
    __CLOCK_LEEWAY_SECONDS: ClassVar[int] = 10

    __AMBIGUOUS_KEY: ClassVar[object] = object()
    __INVALID_KEY: ClassVar[object] = object()

    __jwks_cache: ClassVar[dict[str, tuple[float, float, list[dict[str, object]]]]] = {}
    __jwks_lock: ClassVar[asyncio.Lock | None] = None
    __jwks_lock_loop: ClassVar[asyncio.AbstractEventLoop | None] = None

    def __init__(self, http_client: BasicHttpClientDep) -> None:
        self.__http_client = http_client
        self.__supabase_url = settings.SUPABASE_URL
        self.__supabase_key = settings.SUPABASE_SERVICE_ROLE_KEY

    async def verify(self, token: str) -> VerifiedAccessToken | None:
        if len(token) > AccessTokenPort.__MAX_TOKEN_LENGTH or token.count(".") != 2:
            return None
        if any(part == "" for part in token.split(".")):
            return None

        issuer = self.__issuer(self.__supabase_url)
        if issuer is None:
            return None

        try:
            header = jwt.get_unverified_header(token)
        except PyJWTError:
            return None

        algorithm = header.get("alg")
        if (
            not isinstance(algorithm, str)
            or algorithm not in AccessTokenPort.__ASYMMETRIC_ALGORITHMS
        ):
            return None

        kid = header.get("kid")
        key_id = kid if isinstance(kid, str) and kid else None
        jwks_url = f"{issuer}/.well-known/jwks.json"
        loaded = await self.__load_jwks(jwks_url, force=False)
        if loaded is None:
            return None
        keys, fetched_at = loaded

        signing_key = self.__signing_key_for_token(
            keys, kid=key_id, algorithm=algorithm
        )
        if (
            signing_key is AccessTokenPort.__AMBIGUOUS_KEY
            or signing_key is AccessTokenPort.__INVALID_KEY
        ):
            return None
        if (
            signing_key is None
            and (time.monotonic() - fetched_at)
            > AccessTokenPort.__JWKS_REFRESH_AFTER_SECONDS
        ):
            loaded = await self.__load_jwks(jwks_url, force=True)
            if loaded is None:
                return None
            keys, _fetched_at = loaded
            signing_key = self.__signing_key_for_token(
                keys, kid=key_id, algorithm=algorithm
            )

        if not self.__is_signing_key(signing_key):
            return None

        return self.__identity_from_token(token, signing_key, [algorithm], issuer)

    @classmethod
    def clear_jwks_cache(cls) -> None:
        cls.__jwks_cache.clear()

    async def __load_jwks(
        self,
        url: str,
        *,
        force: bool,
    ) -> tuple[list[dict[str, object]], float] | None:
        now = time.monotonic()
        if not force:
            cached = self.__read_cache(url, now)
            if cached is not None:
                return cached

        async with self.__lock_for_running_loop():
            if not force:
                cached = self.__read_cache(url, time.monotonic())
                if cached is not None:
                    return cached
            try:
                response = await self.__http_client.get(
                    url, headers=self.__jwks_headers(self.__supabase_key)
                )
                response.raise_for_status()
                payload = response.json()
            except httpx.HTTPError, ValueError:
                return None

            keys = self.__jwks_keys(payload)
            if not keys:
                return None
            fetched_at = time.monotonic()
            self.__jwks_cache[url] = (
                fetched_at + AccessTokenPort.__JWKS_TTL_SECONDS,
                fetched_at,
                keys,
            )
            return keys, fetched_at

    @classmethod
    def __read_cache(
        cls, url: str, now: float
    ) -> tuple[list[dict[str, object]], float] | None:
        cached = cls.__jwks_cache.get(url)
        if cached is None or cached[0] <= now:
            return None
        return cached[2], cached[1]

    @classmethod
    def __lock_for_running_loop(cls) -> asyncio.Lock:
        loop = asyncio.get_running_loop()
        if cls.__jwks_lock is None or cls.__jwks_lock_loop is not loop:
            cls.__jwks_lock = asyncio.Lock()
            cls.__jwks_lock_loop = loop
        return cls.__jwks_lock

    @staticmethod
    def __issuer(supabase_url: str) -> str | None:
        base = supabase_url.strip().rstrip("/")
        if not base:
            return None
        return f"{base}/auth/v1"

    @staticmethod
    def __is_signing_key(signing_key: object | None) -> bool:
        return (
            signing_key is not None
            and signing_key is not AccessTokenPort.__AMBIGUOUS_KEY
            and signing_key is not AccessTokenPort.__INVALID_KEY
        )

    @staticmethod
    def __identity_from_token(
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
                audience=AccessTokenPort.__AUTHENTICATED,
                issuer=issuer,
                leeway=AccessTokenPort.__CLOCK_LEEWAY_SECONDS,
                options={"require": ["exp", "iat", "sub", "aud", "iss"]},
            )
        except PyJWTError:
            return None

        if (
            not isinstance(decoded, dict)
            or decoded.get("role") != AccessTokenPort.__AUTHENTICATED
        ):
            return None

        subject = decoded.get("sub")
        if not isinstance(subject, str) or not subject.strip():
            return None

        audience = AccessTokenPort.__audience(decoded.get("aud"))
        if audience is None:
            return None

        issued_at = AccessTokenPort.__unix_time(decoded.get("iat"))
        if issued_at is None:
            return None

        return VerifiedAccessToken(
            user_id=subject,
            audience=audience,
            created_at=AccessTokenPort.__created_at(
                decoded.get("created_at"), issued_at
            ),
        )

    @staticmethod
    def __audience(value: object) -> str | None:
        if value == AccessTokenPort.__AUTHENTICATED:
            return AccessTokenPort.__AUTHENTICATED
        if isinstance(value, list) and AccessTokenPort.__AUTHENTICATED in value:
            return AccessTokenPort.__AUTHENTICATED
        return None

    @staticmethod
    def __created_at(value: object, issued_at: int) -> datetime:
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

    @staticmethod
    def __unix_time(value: object) -> int | None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        return int(value)

    @staticmethod
    def __signing_key_for_token(
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
                return AccessTokenPort.__AMBIGUOUS_KEY
            chosen = item
        if chosen is None:
            return None
        try:
            return PyJWK.from_dict(chosen).key
        except PyJWTError, ValueError, TypeError:
            return AccessTokenPort.__INVALID_KEY

    @staticmethod
    def __jwks_keys(payload: object) -> list[dict[str, object]]:
        if not isinstance(payload, dict):
            return []
        keys = payload.get("keys")
        if not isinstance(keys, list):
            return []
        return [key for key in keys if isinstance(key, dict)]

    @staticmethod
    def __jwks_headers(api_key: str) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        stripped = api_key.strip()
        if stripped:
            headers["apikey"] = stripped
        return headers


AccessTokenPortDep = Annotated[AccessTokenPort, Depends()]
