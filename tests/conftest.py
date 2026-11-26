# Environment values are assigned before application imports so tests cannot
# read .env or real credentials. E402 is expected for the imports below.
# ruff: noqa: E402
import os

os.environ["ENVIRONMENT"] = "testing"
os.environ["SUPABASE_URL"] = "http://supabase.invalid"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "dummy-test-key"
os.environ["AI_API_ENDPOINT"] = "http://ai.invalid"
os.environ["AI_API_KEY"] = "dummy-test-key"
os.environ["DB_HOST"] = "database.invalid"
os.environ["DB_PORT"] = "5432"
os.environ["DB_USER"] = "dummy-test-user"
os.environ["DB_PASSWORD"] = "dummy-test-password"
os.environ["DB_NAME"] = "dummy-test-database"
os.environ["DB_SCHEMA"] = ""

import asyncio
from collections.abc import AsyncGenerator

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from app import create_app
from app.core.config import settings
from app.core.http_client import get_basic_http_client
from app.database import (
    DbSessionManager,
    get_db_session_manager,
    model_common_metadata,
)
from app.ports.ai.ai_port import get_ai_port
from app.ports.supabase import AccessTokenPort, SupabasePort
from app.ports.supabase.spb_port import _get_supabase_client
from tests.fakes.access_token import AccessTokenFake
from tests.fakes.ai import AiApiFake
from tests.fakes.sqlite_supabase import SqliteSupabasePort
from tests.support.access_token import jwks_http_client
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
if (
    settings.DB_HOST != "database.invalid"
    or settings.DB_PASSWORD != "dummy-test-password"
):
    raise RuntimeError("Tests must not use real database credentials")


def _blocked_create_client(*args: object, **kwargs: object) -> None:
    unexpected_interaction("Supabase client construction")


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch):
    install_network_guard(monkeypatch)
    monkeypatch.setattr(
        "app.ports.supabase.spb_port.create_client", _blocked_create_client
    )
    monkeypatch.setattr("supabase.create_client", _blocked_create_client)
    _get_supabase_client.cache_clear()
    AccessTokenPort.clear_jwks_cache()
    try:
        yield
    finally:
        assert_no_unexpected_interactions()
        _get_supabase_client.cache_clear()
        AccessTokenPort.clear_jwks_cache()


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
async def db_session_manager() -> AsyncGenerator[DbSessionManager, None]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(model_common_metadata.create_all)

    manager = DbSessionManager(engine)
    try:
        yield manager
    finally:
        await manager.dispose()


@pytest.fixture
def ai() -> AiApiFake:
    return AiApiFake()


def _use_fakes(app: FastAPI, supabase: SqliteSupabasePort, ai: AiApiFake) -> None:
    app.dependency_overrides[SupabasePort] = lambda: supabase
    app.dependency_overrides[get_ai_port] = lambda: ai
    app.dependency_overrides[AccessTokenPort] = lambda: AccessTokenFake(supabase)


def _use_test_jwks(app: FastAPI, http_client: httpx.AsyncClient) -> None:
    app.dependency_overrides[get_basic_http_client] = lambda: http_client


@pytest.fixture
def client(supabase: SqliteSupabasePort, ai: AiApiFake):
    app = create_app()
    _use_fakes(app, supabase, ai)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def db_client(
    supabase: SqliteSupabasePort,
    ai: AiApiFake,
    db_session_manager: DbSessionManager,
) -> AsyncGenerator[TestClient, None]:
    app = create_app()
    _use_fakes(app, supabase, ai)
    app.dependency_overrides[get_db_session_manager] = lambda: db_session_manager
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def jwks_client(supabase: SqliteSupabasePort, ai: AiApiFake):
    app = create_app()
    http_client = jwks_http_client()
    _use_fakes(app, supabase, ai)
    del app.dependency_overrides[AccessTokenPort]
    _use_test_jwks(app, http_client)
    with TestClient(app) as test_client:
        yield test_client
    asyncio.run(http_client.aclose())


@pytest.fixture
async def jwks_db_client(
    supabase: SqliteSupabasePort,
    ai: AiApiFake,
    db_session_manager: DbSessionManager,
) -> AsyncGenerator[TestClient, None]:
    app = create_app()
    http_client = jwks_http_client()
    _use_fakes(app, supabase, ai)
    del app.dependency_overrides[AccessTokenPort]
    app.dependency_overrides[get_db_session_manager] = lambda: db_session_manager
    _use_test_jwks(app, http_client)
    with TestClient(app) as test_client:
        yield test_client
    await http_client.aclose()
