# Environment values are assigned before application imports so tests cannot
# read .env or real credentials. E402 is expected for the imports below.
# ruff: noqa: E402
import os

os.environ["ENVIRONMENT"] = "testing"
os.environ["SUPABASE_URL"] = "http://supabase.invalid"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "dummy-test-key"
os.environ["AI_API_ENDPOINT"] = "http://ai.invalid"
os.environ["AI_API_KEY"] = "dummy-test-key"

import pytest
from fastapi.testclient import TestClient

from app import create_app
from app.core.config import settings
from app.ports.ai.ai_port import get_ai_port
from app.ports.supabase.spb import SupabasePort, _get_supabase_client
from tests.fakes.ai import AiApiFake
from tests.fakes.sqlite_supabase import SqliteSupabasePort
from tests.support.database import connect_test_database
from tests.support.isolation import (
    assert_no_unexpected_interactions,
    unexpected_interaction,
)
from tests.support.network_guard import install_network_guard

if settings.model_config.get("env_file") is not None:
    raise RuntimeError("Tests must not load an environment file")
if settings.SUPABASE_URL != "http://supabase.invalid":
    raise RuntimeError("Tests must not use a real Supabase URL")
if settings.SUPABASE_SERVICE_ROLE_KEY != "dummy-test-key":
    raise RuntimeError("Tests must not use a real Supabase service role key")
if (
    settings.AI_API_ENDPOINT != "http://ai.invalid"
    or settings.AI_API_KEY != "dummy-test-key"
):
    raise RuntimeError("Tests must not use a real AI credential")


def _blocked_create_client(*args: object, **kwargs: object) -> None:
    unexpected_interaction("Supabase client construction")


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch):
    install_network_guard(monkeypatch)
    monkeypatch.setattr("app.ports.supabase.spb.create_client", _blocked_create_client)
    monkeypatch.setattr("supabase.create_client", _blocked_create_client)
    _get_supabase_client.cache_clear()
    try:
        yield
    finally:
        assert_no_unexpected_interactions()
        _get_supabase_client.cache_clear()


@pytest.fixture
def database():
    connection = connect_test_database()
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def supabase(database) -> SqliteSupabasePort:
    return SqliteSupabasePort(database)


@pytest.fixture
def ai() -> AiApiFake:
    return AiApiFake()


@pytest.fixture
def client(supabase: SqliteSupabasePort, ai: AiApiFake):
    app = create_app()
    app.dependency_overrides[SupabasePort] = lambda: supabase
    app.dependency_overrides[get_ai_port] = lambda: ai
    with TestClient(app) as test_client:
        yield test_client
