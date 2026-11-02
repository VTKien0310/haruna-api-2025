from dataclasses import dataclass
from datetime import date, time


@dataclass
class CheckInEntry:
    id: str
    date: date
    time: time

    @classmethod
    def from_spb_data(cls, data: dict[str, str | int]) -> CheckInEntry:
        return cls(
            id=str(data["id"]),
            date=date.fromisoformat(str(data["date"])),
            time=time.fromisoformat(str(data["time"])),
        )
