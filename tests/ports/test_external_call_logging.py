import logging

import httpx
import pytest

from app.core import apply_log_level_for_application, get_logger, settings
from app.ports.ai import (
    AiApiPort,
    AiJsonObjectResponseFormat,
    AiRequestMessage,
    AiRequestRole,
)
from app.ports.supabase.spb_port import _log_supabase_http_failure, _watch_http_client

_SOURCE_TEXT = "source text that must stay out of the log"


def _stderr_text(record: logging.LogRecord) -> str:
    handler = next(
        handler
        for handler in logging.getLogger("app").handlers
        if handler.name == "app.stderr"
    )
    return handler.format(record)


async def test_ai_http_failure_keeps_the_body_and_omits_secrets(
    caplog: pytest.LogCaptureFixture,
) -> None:
    apply_log_level_for_application("INFO")
    secret = settings.AI_API_KEY

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == f"Bearer {secret}"
        return httpx.Response(502, json={"error": "upstream", "echo": _SOURCE_TEXT})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        port = AiApiPort(
            endpoint="http://ai.invalid",
            api_key=secret,
            http_client=http_client,
            logger=get_logger("ai"),
        )
        with caplog.at_level(logging.WARNING, logger="app.ai"):
            body = await port.chat_completion(
                model="test-model",
                messages=[
                    AiRequestMessage(role=AiRequestRole.USER, content=_SOURCE_TEXT)
                ],
                response_format=AiJsonObjectResponseFormat(),
            )

    assert body == {"error": "upstream", "echo": _SOURCE_TEXT}
    logged = " ".join(caplog.messages)
    assert "operation=chat_completion" in logged
    assert "status=502" in logged
    assert secret not in logged
    assert _SOURCE_TEXT not in logged
    assert "Authorization" not in logged
    assert "[redacted]" not in logged


async def test_ai_transport_error_is_logged_without_the_api_key(
    caplog: pytest.LogCaptureFixture,
) -> None:
    apply_log_level_for_application("INFO")
    secret = settings.AI_API_KEY

    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"connection failed token={secret}?access_token=abc")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        port = AiApiPort(
            endpoint="http://ai.invalid",
            api_key=secret,
            http_client=http_client,
            logger=get_logger("ai"),
        )
        with caplog.at_level(logging.WARNING, logger="app.ai"):
            with pytest.raises(httpx.ConnectError):
                await port.chat_completion(
                    model="test-model",
                    messages=[
                        AiRequestMessage(role=AiRequestRole.USER, content=_SOURCE_TEXT)
                    ],
                    response_format=AiJsonObjectResponseFormat(),
                )

    rendered = _stderr_text(
        next(record for record in caplog.records if record.name == "app.ai")
    )
    assert "error=ConnectError" in rendered
    assert secret not in rendered
    assert "access_token=abc" not in rendered
    assert _SOURCE_TEXT not in rendered


def test_supabase_http_failure_log_omits_keys_and_query(
    caplog: pytest.LogCaptureFixture,
) -> None:
    apply_log_level_for_application("INFO")
    secret = settings.SUPABASE_SERVICE_ROLE_KEY
    http_client = httpx.Client()
    _watch_http_client(http_client)
    _watch_http_client(http_client)
    assert http_client.event_hooks["response"].count(_log_supabase_http_failure) == 1

    request = httpx.Request(
        "GET",
        "http://supabase.invalid/auth/v1/user",
        params={"apikey": secret},
        headers={"Authorization": f"Bearer {secret}", "apikey": secret},
    )
    with caplog.at_level(logging.WARNING, logger="app.supabase"):
        _log_supabase_http_failure(httpx.Response(200, request=request))
        _log_supabase_http_failure(httpx.Response(401, request=request))

    records = [record for record in caplog.records if record.name == "app.supabase"]
    assert len(records) == 1
    rendered = _stderr_text(records[0])
    assert "method=GET" in rendered
    assert "status=401" in rendered
    assert "url=http://supabase.invalid/auth/v1/user" in rendered
    assert secret not in rendered
    assert "apikey" not in rendered
    assert "Authorization" not in rendered
    assert "?" not in rendered
