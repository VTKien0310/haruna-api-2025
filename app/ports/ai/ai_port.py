import httpx
from typing import Annotated
from fastapi import Depends
from .ai_request import AiRequestMessage
from .ai_response import AiResponseFormat
from app.core import LongReadHttpClientDep, settings


class AiApiPort:
    def __init__(
        self, endpoint: str, api_key: str, http_client: httpx.AsyncClient
    ) -> None:
        self.__endpoint = endpoint
        self.__api_key = api_key
        self.__http_client = http_client

    async def chat_completion(
        self,
        model: str,
        messages: list[AiRequestMessage],
        response_format: AiResponseFormat,
    ) -> dict:
        request_body = self.__build_request_body(model, messages, response_format)
        headers = {"Authorization": f"Bearer {self.__api_key}"}
        response = await self.__http_client.post(
            f"{self.__endpoint}/chat/completions", json=request_body, headers=headers
        )
        return response.json()

    def __build_request_body(
        self,
        model: str,
        messages: list[AiRequestMessage],
        response_format: AiResponseFormat,
    ) -> dict:
        return {
            "model": model,
            "messages": list(map(lambda m: m.build(), messages)),
            "response_format": response_format.build(),
        }


def get_ai_port(http_client: LongReadHttpClientDep) -> AiApiPort:
    return AiApiPort(
        endpoint=settings.AI_API_ENDPOINT,
        api_key=settings.AI_API_KEY,
        http_client=http_client,
    )


AiApiPortDep = Annotated[AiApiPort, Depends(get_ai_port)]
