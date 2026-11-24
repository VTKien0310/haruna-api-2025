from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    id: str
    aud: str
    created_at: datetime

    @classmethod
    def from_verified_access_token(
        cls, *, user_id: str, audience: str, created_at: datetime
    ) -> User:
        return cls(id=user_id, aud=audience, created_at=created_at)
