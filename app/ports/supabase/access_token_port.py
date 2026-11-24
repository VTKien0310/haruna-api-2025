import asyncio
import re
import time
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated, ClassVar

import httpx
import jwt
from fastapi import Depends
from jwt import PyJWK, PyJWTError

from app.core import BasicHttpClientDep, get_logger, settings

_QUERY = re.compile(r"\?\S*")

logger = get_logger("auth")


@dataclass(frozen=True)
class VerifiedAccessToken:
    user_id: str
    audience: str
    created_at: datetime


@dataclass(frozen=True)
class AccessTokenFailure:
    reason: str
    alg: str = ""
    kid: str = ""
    iss: str = ""
    error_type: str = ""
    error_message: str = ""


_failure: ContextVar[AccessTokenFailure | None] = ContextVar(
    "access_token_failure", default=None
)


def consume_access_token_failure() -> AccessTokenFailure | None:
    failure = _failure.get()
    _failure.set(None)
    return failure


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
        _failure.set(None)
        if len(token) > AccessTokenPort.__MAX_TOKEN_LENGTH or token.count(".") != 2:
            self.__log_rejection("malformed", token)
            return None
        if any(part == "" for part in token.split(".")):
            self.__log_rejection("malformed", token)
            return None

        issuer = self.__issuer(self.__supabase_url)
        if issuer is None:
            return None

        try:
            header = jwt.get_unverified_header(token)
        except PyJWTError as exc:
            self.__log_rejection("malformed", token, error=exc)
            return None

        algorithm = header.get("alg")
        if (
            not isinstance(algorithm, str)
            or algorithm not in AccessTokenPort.__ASYMMETRIC_ALGORITHMS
        ):
            shown = (
                algorithm[:32]
                if isinstance(algorithm, str)
                else type(algorithm).__name__
            )
            self.__log_rejection("unsupported_algorithm", token, alg=shown)
            return None

        kid = header.get("kid")
        key_id = kid if isinstance(kid, str) and kid else None
        jwks_url = f"{issuer}/.well-known/jwks.json"
        signing_key = await self.__signing_key(jwks_url, key_id, algorithm)
        if not self.__is_signing_key(signing_key):
            # Supabase's edge caches this document for 10 minutes, including an
            # empty set from before asymmetric keys were published. Bypass it once.
            signing_key = await self.__signing_key(
                jwks_url, key_id, algorithm, force=True
            )
        if not self.__is_signing_key(signing_key):
            if _failure.get() is None:
                self.__log_rejection(
                    "jwks_key_not_usable", token, alg=algorithm, kid=key_id or ""
                )
            self.__enrich_failure(token)
            return None

        verified = self.__identity_from_token(token, signing_key, [algorithm], issuer)
        if verified is not None:
            _failure.set(None)
            return verified
        self.__enrich_failure(token)
        return None

    @classmethod
    def clear_jwks_cache(cls) -> None:
        cls.__jwks_cache.clear()

    async def __signing_key(
        self, url: str, key_id: str | None, algorithm: str, *, force: bool = False
    ) -> object | None:
        loaded = await self.__load_jwks(url, force=force)
        if loaded is None:
            return None
        keys, _fetched_at = loaded
        return self.__signing_key_for_token(keys, kid=key_id, algorithm=algorithm)

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
                self.__log_jwks(cache="hit", status="", url=url, keys=cached[0])
                return cached

        async with self.__lock_for_running_loop():
            if not force:
                cached = self.__read_cache(url, time.monotonic())
                if cached is not None:
                    self.__log_jwks(cache="hit", status="", url=url, keys=cached[0])
                    return cached
            try:
                response = await self.__http_client.get(
                    url,
                    headers=self.__jwks_headers(
                        self.__supabase_key, bypass_cache=force
                    ),
                    follow_redirects=True,
                )
                response.raise_for_status()
                payload = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                status = (
                    exc.response.status_code
                    if isinstance(exc, httpx.HTTPStatusError)
                    else ""
                )
                final_url = ""
                if isinstance(exc, httpx.HTTPStatusError):
                    final_url = _public_url(exc.request.url)
                self.__log_jwks(
                    cache="miss",
                    status=status,
                    url=final_url or _public_url(url),
                    keys=[],
                    error=exc,
                )
                self.__log_rejection("jwks_fetch_failed", "", error=exc)
                return None

            keys = self.__jwks_keys(payload)
            self.__log_jwks(
                cache="miss",
                status=response.status_code,
                url=_public_url(response.url),
                keys=keys,
            )
            if not keys:
                self.__log_rejection("jwks_empty", "")
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
        except PyJWTError as exc:
            details: dict[str, object] = {}
            if isinstance(exc, jwt.InvalidIssuerError):
                details["iss"] = AccessTokenPort.__unverified_issuer(token)
            AccessTokenPort.__log_rejection("jwt_rejected", token, error=exc, **details)
            return None

        if not isinstance(decoded, dict):
            AccessTokenPort.__log_rejection("jwt_rejected", token)
            return None
        if decoded.get("role") != AccessTokenPort.__AUTHENTICATED:
            AccessTokenPort.__log_rejection("role_rejected", token)
            return None

        subject = decoded.get("sub")
        if not isinstance(subject, str) or not subject.strip():
            AccessTokenPort.__log_rejection("subject_rejected", token)
            return None

        audience = AccessTokenPort.__audience(decoded.get("aud"))
        if audience is None:
            AccessTokenPort.__log_rejection("audience_rejected", token)
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
    def __jwks_headers(api_key: str, *, bypass_cache: bool) -> dict[str, str]:
        # Match the Supabase Python client: Auth requests send the server key
        # as both apikey and Authorization. The hosted gateway rejects some
        # Auth routes when Authorization is missing.
        headers = {"Accept": "application/json"}
        stripped = api_key.strip()
        if stripped:
            headers["apikey"] = stripped
            headers["Authorization"] = f"Bearer {stripped}"
        if bypass_cache:
            headers["Cache-Control"] = "no-cache"
            headers["Pragma"] = "no-cache"
        return headers

    @staticmethod
    def __unverified_issuer(token: str) -> str:
        try:
            payload = jwt.decode(
                token,
                options={
                    "verify_signature": False,
                    "verify_aud": False,
                    "verify_iss": False,
                    "verify_exp": False,
                },
            )
        except PyJWTError:
            return ""
        issuer = payload.get("iss") if isinstance(payload, dict) else ""
        return issuer if isinstance(issuer, str) else ""

    @staticmethod
    def __log_rejection(
        reason: str,
        token: str = "",
        *,
        error: Exception | None = None,
        **details: object,
    ) -> None:
        alg = str(details.pop("alg", "") or "")
        kid = str(details.pop("kid", "") or "")
        iss = str(details.pop("iss", "") or "")
        if token:
            header_alg, header_kid, claim_iss = AccessTokenPort.__token_hints(token)
            alg = alg or header_alg
            kid = kid or header_kid
            iss = iss or claim_iss
        _failure.set(
            AccessTokenFailure(
                reason=reason,
                alg=alg,
                kid=kid,
                iss=iss,
                error_type=type(error).__name__ if error else "",
                error_message=_safe_message(error) if error else "",
            )
        )

    @staticmethod
    def __log_jwks(
        *,
        cache: str,
        status: object,
        url: str,
        keys: list[dict[str, object]],
        error: Exception | None = None,
    ) -> None:
        kids = ",".join(
            str(item.get("kid", ""))
            for item in keys
            if isinstance(item.get("kid", ""), str)
        )
        if error is None:
            logger.info(
                "jwks fetch cache=%s status=%s url=%s keys=%s kids=%s",
                cache,
                status,
                _public_url(url),
                len(keys),
                kids,
            )
            return
        logger.warning(
            "jwks fetch cache=%s status=%s url=%s keys=%s kids=%s error=%s: %s",
            cache,
            status,
            _public_url(url),
            len(keys),
            kids,
            type(error).__name__,
            _safe_message(error),
        )

    @staticmethod
    def __token_hints(token: str) -> tuple[str, str, str]:
        alg = ""
        kid = ""
        try:
            header = jwt.get_unverified_header(token)
        except PyJWTError:
            header = {}
        if isinstance(header, dict):
            raw_alg = header.get("alg")
            raw_kid = header.get("kid")
            alg = raw_alg[:32] if isinstance(raw_alg, str) else ""
            kid = raw_kid[:128] if isinstance(raw_kid, str) else ""
        return alg, kid, AccessTokenPort.__unverified_issuer(token)

    @staticmethod
    def __enrich_failure(token: str) -> None:
        failure = _failure.get()
        if failure is None:
            return
        alg, kid, iss = AccessTokenPort.__token_hints(token)
        if failure.alg and failure.kid and failure.iss:
            return
        _failure.set(
            AccessTokenFailure(
                reason=failure.reason,
                alg=failure.alg or alg,
                kid=failure.kid or kid,
                iss=failure.iss or iss,
                error_type=failure.error_type,
                error_message=failure.error_message,
            )
        )


def _public_url(url: object) -> str:
    return _QUERY.sub("", str(url))


def _safe_message(error: Exception) -> str:
    return _QUERY.sub("", str(error))


AccessTokenPortDep = Annotated[AccessTokenPort, Depends()]
