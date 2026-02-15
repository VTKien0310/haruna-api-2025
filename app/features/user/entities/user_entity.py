from dataclasses import dataclass
from datetime import datetime

from app.ports import SupabasePortDep


@dataclass
class User:
    id: str
    aud: str
    created_at: datetime

    @classmethod
    def from_spb_data(cls, data: dict[str, str | int | datetime]) -> User:
        return cls(
            id=data["id"],
            aud=data["aud"],
            created_at=data["created_at"],
        )


class UserRepository:
    def __init__(self, supabase: SupabasePortDep):
        self.__supabase = supabase
