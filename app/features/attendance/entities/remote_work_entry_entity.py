from dataclasses import dataclass
from datetime import date
from enum import IntEnum


class RemoteWorkType(IntEnum):
    FULL_DAY = 0
    MORNING = 1
    AFTERNOON = 2


@dataclass
class RemoteWorkEntry:
    id: str
    date: date
    type: RemoteWorkType

    @classmethod
    def from_spb_data(cls, data: dict[str, str | int]) -> RemoteWorkEntry:
        return cls(
            id=str(data["id"]),
            date=date.fromisoformat(str(data["date"])),
            type=RemoteWorkType(int(data["type"])),
        )
