from dataclasses import dataclass
from datetime import date
from enum import IntEnum


class WorkTimeType(IntEnum):
    LATE_FOR_WORK = 0
    LEAVE_WORK_EARLY = 1


@dataclass
class WorkTimeEntry:
    id: str
    date: date
    type: WorkTimeType

    @classmethod
    def from_spb_data(cls, data: dict[str, str | int]) -> WorkTimeEntry:
        return cls(
            id=str(data["id"]),
            date=date.fromisoformat(str(data["date"])),
            type=WorkTimeType(int(data["type"])),
        )
