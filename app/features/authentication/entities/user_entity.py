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
