from dataclasses import dataclass
from datetime import date
from enum import IntEnum


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
    def from_spb_data(cls, data: dict[str, str | int]) -> TimeOffEntry:
        return cls(
            id=str(data["id"]),
            date=date.fromisoformat(str(data["date"])),
            type=TimeOffType(int(data["type"])),
        )
