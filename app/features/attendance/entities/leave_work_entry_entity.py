from dataclasses import dataclass
from datetime import date, time

from app.database import LeaveWorkEntryRecord


@dataclass
class LeaveWorkEntry:
    id: str
    date: date
    start: time
    end: time

    @classmethod
    def from_db_record(cls, record: LeaveWorkEntryRecord) -> LeaveWorkEntry:
        return cls(
            id=str(record.id),
            date=record.date,
            start=record.start,
            end=record.end,
        )

    @classmethod
    def from_spb_data(cls, data: dict[str, str | int]) -> LeaveWorkEntry:
        return cls(
            id=str(data["id"]),
            date=date.fromisoformat(str(data["date"])),
            start=time.fromisoformat(str(data["start"])),
            end=time.fromisoformat(str(data["end"])),
        )
