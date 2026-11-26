import pytest
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.database import DbSessionManager, init_db_session_manager

_CONNECT_ARG_NAMES = {
    "statement_cache_size",
    "prepared_statement_cache_size",
    "timeout",
    "command_timeout",
}


async def _opened_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[DbSessionManager, URL, dict[str, object]]:
    found: list[tuple[URL, dict[str, object]]] = []
    original = create_async_engine

    def capturing(url: URL, **kwargs: object) -> object:
        found.append((url, kwargs))
        return original(url, **kwargs)

    monkeypatch.setattr("app.database.session.create_async_engine", capturing)
    manager = init_db_session_manager()
    url, kwargs = found[0]
    return manager, url, kwargs


async def test_engine_uses_pool_recycle_and_asyncpg_timeouts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manager, url, kwargs = await _opened_engine(monkeypatch)
    try:
        connect_args = kwargs["connect_args"]
        assert kwargs["pool_pre_ping"] is True
        assert kwargs["pool_recycle"] == settings.DB_POOL_RECYCLE_SECONDS == 300
        assert connect_args == {
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
            "timeout": 10,
            "command_timeout": 10,
        }
        assert set(connect_args) == _CONNECT_ARG_NAMES
        assert "server_settings" not in connect_args
        assert url.drivername == "postgresql+asyncpg"
        assert url.host == settings.DB_HOST
        assert url.port == settings.DB_PORT
        assert url.database == settings.DB_NAME
    finally:
        await manager.dispose()


async def test_engine_timeouts_follow_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "DB_POOL_RECYCLE_SECONDS", 120)
    monkeypatch.setattr(settings, "DB_CONNECT_TIMEOUT_SECONDS", 7)
    monkeypatch.setattr(settings, "DB_COMMAND_TIMEOUT_SECONDS", 4)

    manager, _, kwargs = await _opened_engine(monkeypatch)
    try:
        assert kwargs["pool_recycle"] == 120
        assert kwargs["connect_args"]["timeout"] == 7
        assert kwargs["connect_args"]["command_timeout"] == 4
    finally:
        await manager.dispose()
