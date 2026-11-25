import re
from typing import Annotated

import httpx
from fastapi import Depends

from app.core import LongReadHttpClientDep, get_logger_dep, settings

from .ai_request import AiRequestMessage
from .ai_response import AiResponseFormat

_QUERY = re.compile(r"\?\S*")


class AiApiPort:
    def __init__(
        self,
        endpoint: str,
        api_key: str,
        http_client: httpx.AsyncClient,
        logger: get_logger_dep("ai"),
    ) -> None:
        self.__endpoint = endpoint
        self.__api_key = api_key
        self.__http_client = http_client
        self.__logger = logger

    async def chat_completion(
        self,
        model: str,
        messages: list[AiRequestMessage],
        response_format: AiResponseFormat,
    ) -> dict:
        request_body = self.__build_request_body(model, messages, response_format)
        headers = {"Authorization": f"Bearer {self.__api_key}"}
        try:
            response = await self.__http_client.post(
                f"{self.__endpoint}/chat/completions",
                json=request_body,
                headers=headers,
            )
        except httpx.HTTPError as exc:
            self.__log_failure(error=exc)
            raise
        if response.status_code >= 400:
            self.__log_failure(status_code=response.status_code)
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

    def __log_failure(
        self, *, status_code: int | None = None, error: Exception | None = None
    ) -> None:
        if error is None:
            self.__logger.warning(
                "ai request failed operation=chat_completion status=%s",
                status_code,
            )
            return
        self.__logger.warning(
            "ai request failed operation=chat_completion status=%s error=%s: %s",
            "" if status_code is None else status_code,
            type(error).__name__,
            _QUERY.sub("", str(error)),
        )


def get_ai_port(
    http_client: LongReadHttpClientDep, logger: get_logger_dep("ai")
) -> AiApiPort:
    return AiApiPort(
        endpoint=settings.AI_API_ENDPOINT,
        api_key=settings.AI_API_KEY,
        http_client=http_client,
        logger=logger,
    )


AiApiPortDep = Annotated[AiApiPort, Depends(get_ai_port)]
