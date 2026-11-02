from dataclasses import dataclass
from datetime import datetime


@dataclass
class PtoTransaction:
    id: str
    pto_bank_id: str
    entry_id: str
    cause: str
    value: int
    created_at: datetime

    @classmethod
    def from_spb_data(cls, data: dict[str, str | int]) -> PtoTransaction:
        return cls(
            id=str(data["id"]),
            pto_bank_id=str(data["pto_bank_id"]),
            entry_id=str(data["entry_id"]),
            cause=str(data["cause"]),
            value=int(data["value"]),
            created_at=datetime.fromisoformat(str(data["created_at"])),
        )
