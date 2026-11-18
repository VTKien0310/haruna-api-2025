from dataclasses import dataclass
from datetime import date, time

from app.database import CheckInEntryRecord


@dataclass
class CheckInEntry:
    id: str
    date: date
    time: time

    @classmethod
    def from_db_record(cls, record: CheckInEntryRecord) -> CheckInEntry:
        return cls(
            id=str(record.id),
            date=record.date,
            time=record.time,
        )

    @classmethod
    def from_spb_data(cls, data: dict[str, str | int]) -> CheckInEntry:
        return cls(
            id=str(data["id"]),
            date=date.fromisoformat(str(data["date"])),
            time=time.fromisoformat(str(data["time"])),
        )
