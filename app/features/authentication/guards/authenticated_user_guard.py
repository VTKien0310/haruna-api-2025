from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.features.authentication.entities import User
from app.ports.access_token import (
    AccessTokenVerifierPort,
    AccessTokenVerifierPortDep,
    VerifiedAccessToken,
)

security = HTTPBearer()


async def _get_user_from_supabase_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    verifier: AccessTokenVerifierPortDep,
) -> User:
    verified = await _verified_access_token(verifier, credentials.credentials)
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


async def _verified_access_token(
    verifier: AccessTokenVerifierPort, token: str
) -> VerifiedAccessToken | None:
    try:
        return await verifier.verify(token)
    except Exception:
        return None


AuthenticatedGuardDep = Depends(_get_user_from_supabase_token)
CurrentAuthenticatedUserDep = Annotated[User, Depends(_get_user_from_supabase_token)]
