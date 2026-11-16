from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum

from app.database import UserSpecialPermissionRecord


class SpecialPermission(IntEnum):
    MANAGE_WORKDAY_EXCEPTIONS = 0


@dataclass
class UserSpecialPermission:
    id: int
    user_id: str
    permission: SpecialPermission
    created_at: datetime

    @classmethod
    def from_db_record(
        cls, record: UserSpecialPermissionRecord
    ) -> UserSpecialPermission:
        return cls(
            id=int(record.id) if record.id is not None else 0,
            user_id=str(record.user_id),
            permission=SpecialPermission(record.permission),
            created_at=record.created_at,
        )
