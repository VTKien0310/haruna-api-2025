from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.ports.supabase import SupabasePortDep
from app.features.auth.entities import User

security = HTTPBearer()


async def _get_user_from_supabase_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    supabase: SupabasePortDep,
) -> User:
    token = credentials.credentials

    try:
        spb_response = supabase.auth().get_user(token)
        if spb_response is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return User.from_spb_auth(spb_response.user)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


AuthenticatedGuardDep = Depends(_get_user_from_supabase_token)
CurrentAuthenticatedUserDep = Annotated[User, Depends(_get_user_from_supabase_token)]
