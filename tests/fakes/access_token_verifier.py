from app.ports.access_token import VerifiedAccessToken
from tests.fakes.sqlite_supabase import SqliteSupabasePort


class AccessTokenVerifierFake:
    """In-memory stand-in: a registered bearer label verifies as that user."""

    def __init__(self, supabase: SqliteSupabasePort) -> None:
        self.__supabase = supabase

    async def verify(self, token: str) -> VerifiedAccessToken | None:
        user = self.__supabase.auth().registered_user(token)
        if user is None:
            return None
        return VerifiedAccessToken(
            user_id=user.id,
            audience=user.aud,
            created_at=user.created_at,
        )
