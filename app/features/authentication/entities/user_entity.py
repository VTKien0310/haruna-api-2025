from dataclasses import dataclass
from datetime import datetime

from supabase_auth import User as SupabaseAuthUser


@dataclass
class User:
    id: str
    aud: str
    created_at: datetime

    @classmethod
    def from_spb_auth(cls, supabase_auth: SupabaseAuthUser) -> User:
        return cls(
            id=supabase_auth.id,
            aud=supabase_auth.aud,
            created_at=supabase_auth.created_at,
        )

    @classmethod
    def from_verified_access_token(
        cls, *, user_id: str, audience: str, created_at: datetime
    ) -> User:
        return cls(id=user_id, aud=audience, created_at=created_at)
