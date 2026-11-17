from dataclasses import dataclass
from datetime import date

from app.database import MissCheckInEntryRecord


@dataclass
class MissCheckInEntry:
    id: str
    date: date
    penalty: int

    @classmethod
    def from_db_record(cls, record: MissCheckInEntryRecord) -> MissCheckInEntry:
        return cls(
            id=str(record.id),
            date=record.date,
            penalty=record.penalty,
        )
