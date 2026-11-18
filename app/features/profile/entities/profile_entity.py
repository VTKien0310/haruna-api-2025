from dataclasses import dataclass
from datetime import date, datetime

from app.database import ProfileRecord


@dataclass
class Profile:
    id: str
    user_id: str | None
    name: str | None
    birth_date: date
    work_start_date: date
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db_record(cls, record: ProfileRecord) -> Profile:
        return cls(
            id=str(record.id),
            user_id=str(record.user_id) if record.user_id else None,
            name=record.name,
            birth_date=record.birth_date,
            work_start_date=record.work_start_date,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    @classmethod
    def from_spb_data(cls, data: dict[str, str | int]) -> Profile:
        return cls(
            id=str(data["id"]),
            user_id=str(data["user_id"]) if data["user_id"] else None,
            name=str(data["name"]) if data["name"] else None,
            birth_date=date.fromisoformat(str(data["birth_date"])),
            work_start_date=date.fromisoformat(str(data["work_start_date"])),
            created_at=datetime.fromisoformat(str(data["created_at"])),
            updated_at=datetime.fromisoformat(str(data["updated_at"])),
        )
