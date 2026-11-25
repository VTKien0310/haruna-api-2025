import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core import get_logger_dep, logger_dependency
from tests.factories.database_records import TEST_USER_ID
from tests.fakes.sqlite_supabase import SqliteSupabasePort


class _Capture(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def test_get_logger_dep_resolves_the_named_logger() -> None:
    app = FastAPI()

    @app.get("/logger")
    def read_logger(logger: get_logger_dep("auth")) -> dict[str, str]:
        return {"name": logger.name}

    with TestClient(app) as client:
        response = client.get("/logger")

    assert response.status_code == 200
    assert response.json() == {"name": "app.auth"}
    assert logger_dependency("auth") is logger_dependency("app.auth")


def test_auth_logger_dependency_can_be_overridden(
    client: TestClient,
    supabase: SqliteSupabasePort,
    caplog: pytest.LogCaptureFixture,
) -> None:
    supabase.auth().register("token-1", user_id=TEST_USER_ID)
    capture = _Capture()
    override = logging.getLogger("test.override.auth")
    override.handlers.clear()
    override.setLevel(logging.INFO)
    override.propagate = False
    override.addHandler(capture)
    client.app.dependency_overrides[logger_dependency("auth")] = lambda: override

    with caplog.at_level(logging.INFO, logger="app.auth"):
        response = client.post(
            "/api/medias/missing/thumbnails",
            json={"width": 8, "height": 8},
            headers={"Authorization": "Bearer token-1"},
        )

    assert response.status_code == 404
    assert any("path=local" in message for message in capture.messages)
    assert not any("path=local" in message for message in caplog.messages)
