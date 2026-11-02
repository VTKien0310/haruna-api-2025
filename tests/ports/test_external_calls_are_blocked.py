import httpx
import pytest

from app.ports.ai import (
    AiApiPort,
    AiJsonObjectResponseFormat,
    AiRequestMessage,
    AiRequestRole,
)
from app.ports.supabase import SupabasePort
from tests.fakes.ai import AiApiFake
from tests.support.isolation import assert_no_unexpected_interactions


async def test_ai_fake_returns_a_queued_response(ai: AiApiFake) -> None:
    ai.queue_chat_completion({"translation": "hello"})

    result = await ai.chat_completion(
        "test-model",
        [AiRequestMessage(content="hello", role=AiRequestRole.USER)],
        AiJsonObjectResponseFormat(),
    )

    assert result == {"translation": "hello"}
    assert len(ai.calls) == 1


async def test_ai_fake_rejects_an_unconfigured_call(ai: AiApiFake) -> None:
    with pytest.raises(RuntimeError, match="AI chat completion"):
        await ai.chat_completion("test-model", [], AiJsonObjectResponseFormat())
    with pytest.raises(AssertionError, match="AI chat completion"):
        assert_no_unexpected_interactions()


async def test_ai_port_cannot_open_a_connection() -> None:
    async with httpx.AsyncClient() as http_client:
        port = AiApiPort("http://ai.invalid", "dummy-test-key", http_client)
        with pytest.raises(RuntimeError, match="Unexpected external interaction"):
            await port.chat_completion(
                "test-model",
                [AiRequestMessage(content="hello", role=AiRequestRole.USER)],
                AiJsonObjectResponseFormat(),
            )
    with pytest.raises(AssertionError, match="Unexpected external interaction"):
        assert_no_unexpected_interactions()


def test_real_supabase_port_cannot_be_constructed() -> None:
    with pytest.raises(RuntimeError, match="Supabase client construction"):
        SupabasePort()
    with pytest.raises(AssertionError, match="Supabase client construction"):
        assert_no_unexpected_interactions()
