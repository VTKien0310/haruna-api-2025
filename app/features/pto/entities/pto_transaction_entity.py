from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.database import PtoTransactionRecord
from app.features.pto.entities.pto_affect_entry_entity import PtoAffectEntryType


class PtoTransactionCause(StrEnum):
    CHECK_IN_CREATE = "check_in_entries_create"
    TIME_OFF_CREATE = "time_off_entries_create"
    LEAVE_WORK_CREATE = "leave_work_entries_create"
    WORK_TIME_CREATE = "work_time_entries_create"
    REMOTE_WORK_CREATE = "remote_work_entries_create"

    @classmethod
    def from_entry_create(cls, entry_type: PtoAffectEntryType) -> PtoTransactionCause:
        return cls(f"{entry_type.value}_create")


@dataclass
class PtoTransaction:
    id: str
    pto_bank_id: str
    entry_id: str
    cause: PtoTransactionCause
    value: int
    exceed_bank_value: int
    created_at: datetime

    @classmethod
    def from_db_record(cls, record: PtoTransactionRecord) -> PtoTransaction:
        return cls(
            id=str(record.id),
            pto_bank_id=str(record.pto_bank_id),
            entry_id=str(record.entry_id),
            cause=PtoTransactionCause(record.cause),
            value=record.value,
            exceed_bank_value=record.exceed_bank_value,
            created_at=record.created_at,
        )

    @classmethod
    def from_spb_data(cls, data: dict[str, str | int]) -> PtoTransaction:
        return cls(
            id=str(data["id"]),
            pto_bank_id=str(data["pto_bank_id"]),
            entry_id=str(data["entry_id"]),
            cause=PtoTransactionCause(str(data["cause"])),
            value=int(data["value"]),
            exceed_bank_value=int(data.get("exceed_bank_value", 0)),
            created_at=datetime.fromisoformat(str(data["created_at"])),
        )
