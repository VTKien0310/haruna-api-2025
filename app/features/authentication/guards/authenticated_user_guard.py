import asyncio
import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.features.authentication.entities import User
from app.ports.supabase import (
    AccessTokenPortDep,
    SupabasePortDep,
    VerifiedAccessToken,
)

logger = logging.getLogger(__name__)
security = HTTPBearer()


async def _get_user_from_supabase_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    verifier: AccessTokenPortDep,
    supabase: SupabasePortDep,
) -> User:
    token = credentials.credentials
    verified: VerifiedAccessToken | None = None
    try:
        verified = await verifier.verify(token)
    except Exception as exc:
        logger.exception(
            "Access token verification failed; falling back to Supabase Auth: %s", exc
        )
        try:
            spb_response = await asyncio.to_thread(supabase.auth().get_user, token)
            if spb_response is not None and spb_response.user is not None:
                return User.from_spb_auth(spb_response.user)
        except Exception as exc:
            logger.exception("Supabase Auth user lookup failed: %s", exc)

    if verified is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return User.from_verified_access_token(
        user_id=verified.user_id,
        audience=verified.audience,
        created_at=verified.created_at,
    )


AuthenticatedGuardDep = Depends(_get_user_from_supabase_token)
CurrentAuthenticatedUserDep = Annotated[User, Depends(_get_user_from_supabase_token)]
