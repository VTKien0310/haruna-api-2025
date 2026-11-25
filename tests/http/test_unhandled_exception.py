import logging

import pytest
from fastapi.testclient import TestClient

from app import create_app
from app.core.config import settings


def test_unhandled_exception_logs_the_traceback_and_keeps_the_response(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app()

    @app.get("/__unhandled_exception")
    def _boom() -> None:
        raise RuntimeError(settings.DB_PASSWORD)

    with TestClient(app, raise_server_exceptions=False) as client:
        with caplog.at_level(logging.ERROR, logger="app.error"):
            response = client.get("/__unhandled_exception")

    assert response.status_code == 500
    assert response.text == "Internal Server Error"
    assert response.headers["content-type"].startswith("text/plain")
    assert "x-process-time" not in {name.lower() for name in response.headers}
    assert settings.DB_PASSWORD not in response.text

    messages = " ".join(caplog.messages)
    assert "unhandled exception" in messages
    assert "method=GET" in messages
    assert "path=/__unhandled_exception" in messages
    assert "error=RuntimeError" in messages
    assert settings.DB_PASSWORD not in messages
    assert settings.DB_PASSWORD not in caplog.text
    assert "Traceback (most recent call last)" in caplog.text
