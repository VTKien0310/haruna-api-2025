from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core import BasicHttpClientDep, settings
from app.features.authentication.entities import User
from app.ports.supabase import (
    VerifiedSupabaseAccessToken,
    verify_supabase_access_token,
)

security = HTTPBearer()


async def _get_user_from_supabase_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    http_client: BasicHttpClientDep,
) -> User:
    verdict = await _verified_access_token(credentials.credentials, http_client)
    if verdict is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return User.from_verified_access_token(
        user_id=verdict.user_id,
        audience=verdict.audience,
        created_at=verdict.created_at,
    )


async def _verified_access_token(
    token: str, http_client: BasicHttpClientDep
) -> VerifiedSupabaseAccessToken | None:
    try:
        verdict = await verify_supabase_access_token(
            token,
            http_client=http_client,
            supabase_url=settings.SUPABASE_URL,
            supabase_key=settings.SUPABASE_SERVICE_ROLE_KEY,
        )
    except Exception:
        return None
    if isinstance(verdict, VerifiedSupabaseAccessToken):
        return verdict
    return None


AuthenticatedGuardDep = Depends(_get_user_from_supabase_token)
CurrentAuthenticatedUserDep = Annotated[User, Depends(_get_user_from_supabase_token)]
