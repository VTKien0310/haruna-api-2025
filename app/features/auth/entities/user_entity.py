from dataclasses import dataclass
from datetime import datetime
from supabase_auth import User as SupabaseAuthUser
from app.ports import SupabasePortDep
from typing import Annotated
from fastapi import Depends


@dataclass
class User:
    id: str
    aud: str
    created_at: datetime


class UserRepository:
    def __init__(self, supabase: SupabasePortDep):
        self.__supabase = supabase

    @classmethod
    def user_from_spb_auth(cls, supabase_auth: SupabaseAuthUser) -> User:
        return User(
            id=supabase_auth.id,
            aud=supabase_auth.aud,
            created_at=supabase_auth.created_at,
        )


UserRepositoryDep = Annotated[UserRepository, Depends()]
