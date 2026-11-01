from dataclasses import dataclass
from datetime import date, datetime
from enum import IntEnum


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
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_spb_data(cls, data: dict[str, str | int]) -> WorkdayException:
        return cls(
            id=str(data["id"]),
            type=WorkdayExceptionType(int(data["type"])),
            date=date.fromisoformat(str(data["date"])),
            time=WorkdayExceptionTime(int(data["time"])),
            created_at=datetime.fromisoformat(str(data["created_at"])),
            updated_at=datetime.fromisoformat(str(data["updated_at"])),
        )
