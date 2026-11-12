from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.database import PtoAffectEntryRecord


class PtoAffectEntryType(StrEnum):
    CHECK_IN = "check_in_entries"
    TIME_OFF = "time_off_entries"
    LEAVE_WORK = "leave_work_entries"
    WORK_TIME = "work_time_entries"
    REMOTE_WORK = "remote_work_entries"


@dataclass
class PtoAffectEntry:
    id: str
    owner_id: str
    entry_id: str | None
    entry_type: PtoAffectEntryType | None
    no_deduction: bool
    note: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db_record(cls, record: PtoAffectEntryRecord) -> PtoAffectEntry:
        return cls(
            id=str(record.id),
            owner_id=str(record.owner_id),
            entry_id=str(record.entry_id) if record.entry_id is not None else None,
            entry_type=PtoAffectEntryType(record.entry_type)
            if record.entry_type is not None
            else None,
            no_deduction=bool(record.no_deduction),
            note=record.note,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    @classmethod
    def from_spb_data(cls, data: dict[str, str | int]) -> PtoAffectEntry:
        return cls(
            id=str(data["id"]),
            owner_id=str(data["owner_id"]),
            entry_id=str(data["entry_id"]) if data["entry_id"] else None,
            entry_type=PtoAffectEntryType(str(data["entry_type"]))
            if data["entry_type"]
            else None,
            no_deduction=bool(int(data["no_deduction"])),
            note=str(data["note"]),
            created_at=datetime.fromisoformat(str(data["created_at"])),
            updated_at=datetime.fromisoformat(str(data["updated_at"])),
        )
