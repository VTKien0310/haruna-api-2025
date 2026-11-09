from dataclasses import dataclass
from datetime import date
from enum import IntEnum

from app.database import WorkTimeEntryRecord


class WorkTimeType(IntEnum):
    LATE_FOR_WORK = 0
    LEAVE_WORK_EARLY = 1


class WorkTimeShift(IntEnum):
    MORNING = 0
    AFTERNOON = 1


@dataclass
class WorkTimeEntry:
    id: str
    date: date
    type: WorkTimeType
    duration: int
    time: WorkTimeShift

    @classmethod
    def from_db_record(cls, record: WorkTimeEntryRecord) -> WorkTimeEntry:
        return cls(
            id=str(record.id),
            date=record.date,
            type=WorkTimeType(record.type),
            duration=record.duration,
            time=WorkTimeShift(record.time),
        )

    @classmethod
    def from_spb_data(cls, data: dict[str, str | int]) -> WorkTimeEntry:
        return cls(
            id=str(data["id"]),
            date=date.fromisoformat(str(data["date"])),
            type=WorkTimeType(int(data["type"])),
            duration=int(data["duration"]),
            time=WorkTimeShift(int(data["time"])),
        )
