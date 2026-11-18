from app.ports.ai import AiRequestMessage
from app.ports.ai.ai_response import AiResponseFormat
from tests.support.isolation import unexpected_interaction


class AiApiFake:
    def __init__(self) -> None:
        self._responses: list[dict[str, object]] = []
        self.calls: list[dict[str, object]] = []

    def queue_chat_completion(self, payload: dict[str, object]) -> None:
        self._responses.append(payload)

    async def chat_completion(
        self,
        model: str,
        messages: list[AiRequestMessage],
        response_format: AiResponseFormat,
    ) -> dict[str, object]:
        self.calls.append(
            {
                "model": model,
                "messages": messages,
                "response_format": response_format,
            }
        )
        if not self._responses:
            unexpected_interaction("AI chat completion")
        return self._responses.pop(0)
