from dataclasses import dataclass
from datetime import datetime

from app.database import PtoTransactionRecord


@dataclass
class PtoTransaction:
    id: str
    pto_bank_id: str
    entry_id: str
    cause: str
    value: int
    exceed_bank_value: int
    created_at: datetime

    @classmethod
    def from_db_record(cls, record: PtoTransactionRecord) -> PtoTransaction:
        return cls(
            id=str(record.id),
            pto_bank_id=str(record.pto_bank_id),
            entry_id=str(record.entry_id),
            cause=record.cause,
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
            cause=str(data["cause"]),
            value=int(data["value"]),
            exceed_bank_value=int(data.get("exceed_bank_value", 0)),
            created_at=datetime.fromisoformat(str(data["created_at"])),
        )
