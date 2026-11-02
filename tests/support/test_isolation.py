import socket

import pytest

from app.core.config import settings
from tests.support.isolation import (
    assert_no_unexpected_interactions,
    unexpected_interaction,
)


def test_settings_do_not_load_an_environment_file() -> None:
    assert settings.model_config.get("env_file") is None
    assert settings.ENVIRONMENT == "testing"
    assert settings.SUPABASE_URL == "http://supabase.invalid"
    assert settings.SUPABASE_SERVICE_ROLE_KEY == "dummy-test-key"
    assert settings.AI_API_ENDPOINT == "http://ai.invalid"
    assert settings.AI_API_KEY == "dummy-test-key"


def test_network_guard_blocks_outbound_sockets() -> None:
    with pytest.raises(RuntimeError, match="network connection"):
        socket.create_connection(("example.invalid", 80))
    with pytest.raises(AssertionError, match="network connection"):
        assert_no_unexpected_interactions()


def test_unexpected_interaction_is_still_reported_after_it_is_caught() -> None:
    try:
        unexpected_interaction("example call")
    except RuntimeError:
        pass
    with pytest.raises(AssertionError, match="example call"):
        assert_no_unexpected_interactions()
