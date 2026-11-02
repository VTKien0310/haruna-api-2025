from dataclasses import dataclass
from datetime import datetime


@dataclass
class PtoBank:
    id: str
    owner_id: str
    annual_balance: int
    extended_balance: int
    seniority_balance: int
    year: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_spb_data(cls, data: dict[str, str | int]) -> PtoBank:
        return cls(
            id=str(data["id"]),
            owner_id=str(data["owner_id"]),
            annual_balance=int(data["annual_balance"]),
            extended_balance=int(data["extended_balance"]),
            seniority_balance=int(data["seniority_balance"]),
            year=int(data["year"]),
            created_at=datetime.fromisoformat(str(data["created_at"])),
            updated_at=datetime.fromisoformat(str(data["updated_at"])),
        )
