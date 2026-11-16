from dataclasses import dataclass
from datetime import date
from enum import IntEnum

from app.database import TimeOffEntryRecord


class TimeOffType(IntEnum):
    FULL_DAY = 0
    MORNING = 1
    AFTERNOON = 2


@dataclass
class TimeOffEntry:
    id: str
    date: date
    type: TimeOffType

    @classmethod
    def from_db_record(cls, record: TimeOffEntryRecord) -> TimeOffEntry:
        return cls(
            id=str(record.id),
            date=record.date,
            type=TimeOffType(record.type),
        )

    @classmethod
    def from_spb_data(cls, data: dict[str, str | int]) -> TimeOffEntry:
        return cls(
            id=str(data["id"]),
            date=date.fromisoformat(str(data["date"])),
            type=TimeOffType(int(data["type"])),
        )
