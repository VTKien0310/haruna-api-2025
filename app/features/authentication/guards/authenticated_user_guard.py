import asyncio
import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.features.authentication.entities import User
from app.features.authentication.logger import AuthenticationLoggerDep
from app.ports.supabase import AccessTokenPortDep, SupabasePortDep
from app.ports.supabase.spb_access_token_port import (
    AccessTokenFailure,
    consume_access_token_failure,
)

security = HTTPBearer()


async def _get_user_from_supabase_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    verifier: AccessTokenPortDep,
    supabase: SupabasePortDep,
    logger: AuthenticationLoggerDep,
) -> User:
    token = credentials.credentials
    local_error: Exception | None = None
    try:
        verified = await verifier.verify(token)
    except Exception as exc:
        local_error = exc
        verified = None

    if verified is not None:
        logger.info("access token authenticated path=local")
        return User.from_verified_access_token(
            user_id=verified.user_id,
            audience=verified.audience,
            created_at=verified.created_at,
        )

    fallback_error: Exception | None = None
    try:
        spb_response = await asyncio.to_thread(supabase.auth().get_user, token)
    except Exception as exc:
        fallback_error = exc
        spb_response = None

    if spb_response is not None and spb_response.user is not None:
        _log_local_failure(logger, local_error, fallback="succeeded")
        logger.info("access token authenticated path=fallback")
        return User.from_spb_auth(spb_response.user)

    _log_local_failure(
        logger, local_error, fallback="failed", fallback_error=fallback_error
    )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _log_local_failure(
    logger: logging.Logger,
    local_error: Exception | None,
    *,
    fallback: str,
    fallback_error: Exception | None = None,
) -> None:
    failure = consume_access_token_failure()
    if failure is None:
        failure = AccessTokenFailure(
            reason="unexpected" if local_error is not None else "rejected",
            error_type=type(local_error).__name__ if local_error else "",
            error_message=str(local_error) if local_error else "",
        )
    fallback_type = type(fallback_error).__name__ if fallback_error else ""
    fallback_message = str(fallback_error) if fallback_error else ""
    logger.warning(
        "access token rejected reason=%s error=%s: %s alg=%s kid=%s iss=%s "
        "fallback=%s fallback_error=%s: %s",
        failure.reason,
        failure.error_type,
        failure.error_message,
        failure.alg,
        failure.kid,
        failure.iss,
        fallback,
        fallback_type,
        fallback_message,
    )


AuthenticatedGuardDep = Depends(_get_user_from_supabase_token)
CurrentAuthenticatedUserDep = Annotated[User, Depends(_get_user_from_supabase_token)]
