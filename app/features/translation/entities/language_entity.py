from dataclasses import dataclass


@dataclass(frozen=True)
class Language:
    code: str
    name: str

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> Language:
        return cls(code=data["code"], name=data["name"])
