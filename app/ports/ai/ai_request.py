from dataclasses import dataclass
from enum import StrEnum


class AiRequestRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass(frozen=True)
class AiRequestMessage:
    content: str
    role: AiRequestRole

    def build(self) -> dict:
        return {"role": self.role.value, "content": self.content}
