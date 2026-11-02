from dataclasses import dataclass
from datetime import date, datetime


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
