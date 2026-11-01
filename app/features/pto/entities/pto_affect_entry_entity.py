from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class PtoAffectEntryType(StrEnum):
    CHECK_IN = "check_in_entries"
    TIME_OFF = "time_off_entries"
    LEAVE_WORK = "leave_work_entries"
    WORK_TIME = "work_time_entries"
    REMOTE_WORK = "remote_work_entries"


@dataclass
class PtoAffectEntry:
    id: str
    entry_id: str | None
    entry_type: PtoAffectEntryType | None
    no_deduction: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_spb_data(cls, data: dict[str, str | int]) -> PtoAffectEntry:
        return cls(
            id=str(data["id"]),
            entry_id=str(data["entry_id"]) if data["entry_id"] else None,
            entry_type=PtoAffectEntryType(str(data["entry_type"]))
            if data["entry_type"]
            else None,
            no_deduction=bool(int(data["no_deduction"])),
            created_at=datetime.fromisoformat(str(data["created_at"])),
            updated_at=datetime.fromisoformat(str(data["updated_at"])),
        )
