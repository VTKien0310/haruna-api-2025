from dataclasses import dataclass
from datetime import date, datetime
from enum import IntEnum

from app.database import WorkdayExceptionRecord


class WorkdayExceptionType(IntEnum):
    WORKDAY = 0
    HOLIDAY = 1


class WorkdayExceptionTime(IntEnum):
    FULL_DAY = 0
    MORNING = 1
    AFTERNOON = 2


@dataclass
class WorkdayException:
    id: str
    type: WorkdayExceptionType
    date: date
    time: WorkdayExceptionTime
    title: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_spb_data(cls, data: dict[str, str | int]) -> WorkdayException:
        return cls(
            id=str(data["id"]),
            title=str(data["title"]),
            type=WorkdayExceptionType(int(data["type"])),
            date=date.fromisoformat(str(data["date"])),
            time=WorkdayExceptionTime(int(data["time"])),
            created_at=datetime.fromisoformat(str(data["created_at"])),
            updated_at=datetime.fromisoformat(str(data["updated_at"])),
        )

    @classmethod
    def from_db_record(cls, record: WorkdayExceptionRecord) -> WorkdayException:
        return cls(
            id=str(record.id),
            type=WorkdayExceptionType(record.type),
            date=record.date,
            time=WorkdayExceptionTime(record.time),
            title=record.title,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
