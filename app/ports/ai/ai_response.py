from abc import ABC, abstractmethod


class AiResponseFormat(ABC):
    type: str

    @abstractmethod
    def build(self) -> dict:
        pass


class AiJsonObjectResponseFormat(AiResponseFormat):
    type = "json_object"

    def build(self) -> dict:
        return {"type": self.type}


class AiJsonSchemaResponseFormat(AiResponseFormat):
    type = "json_schema"
    name: str
    props: dict
    required: list[str]

    def __init__(self, name: str, props: dict, required: list[str]):
        self.name = name
        self.props = props
        self.required = required

    def build(self) -> dict:
        return {
            "type": self.type,
            "json_schema": {
                "name": self.name,
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": self.props,
                    "required": self.required,
                    "additionalProperties": False,
                },
            },
        }
