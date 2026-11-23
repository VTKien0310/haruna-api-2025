import asyncio
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core import BasicHttpClientDep, settings
from app.features.authentication.entities import User
from app.ports.supabase import (
    RejectedSupabaseAccessToken,
    SupabasePortDep,
    UnresolvedSupabaseAccessToken,
    VerifiedSupabaseAccessToken,
    verify_supabase_access_token,
)

security = HTTPBearer()


async def _get_user_from_supabase_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    supabase: SupabasePortDep,
    http_client: BasicHttpClientDep,
) -> User:
    user = await _user_from_access_token(credentials.credentials, supabase, http_client)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def _user_from_access_token(
    token: str, supabase: SupabasePortDep, http_client: BasicHttpClientDep
) -> User | None:
    try:
        verdict = await verify_supabase_access_token(
            token,
            http_client=http_client,
            supabase_url=settings.SUPABASE_URL,
            jwt_secret=settings.SUPABASE_JWT_SECRET,
            supabase_key=settings.SUPABASE_SERVICE_ROLE_KEY,
        )
    except Exception:
        verdict = UnresolvedSupabaseAccessToken()

    if isinstance(verdict, VerifiedSupabaseAccessToken):
        return User.from_verified_access_token(
            user_id=verdict.user_id,
            audience=verdict.audience,
            created_at=verdict.created_at,
        )
    if isinstance(verdict, RejectedSupabaseAccessToken):
        return None
    return await _user_from_auth_server(token, supabase)


async def _user_from_auth_server(token: str, supabase: SupabasePortDep) -> User | None:
    try:
        spb_response = await asyncio.to_thread(supabase.auth().get_user, token)
    except Exception:
        return None

    if spb_response is None or spb_response.user is None:
        return None

    try:
        return User.from_spb_auth(spb_response.user)
    except Exception:
        return None


AuthenticatedGuardDep = Depends(_get_user_from_supabase_token)
CurrentAuthenticatedUserDep = Annotated[User, Depends(_get_user_from_supabase_token)]
