import logging

import pytest
from fastapi.testclient import TestClient

from app import create_app
from app.core.config import settings


def _freeze_elapsed_ms(monkeypatch: pytest.MonkeyPatch, elapsed_ms: float) -> None:
    """Replace only the middleware clock.

    Patching ``time.perf_counter`` on the stdlib module would also feed every
    other caller during the request and exhaust the scripted samples.
    """

    class _Clock:
        def __init__(self) -> None:
            self.__end = elapsed_ms / 1000
            self.__started = False

        def perf_counter(self) -> float:
            if not self.__started:
                self.__started = True
                return 0.0
            return self.__end

    monkeypatch.setattr(
        "app.http.middlewares.request_timing_middleware.time",
        _Clock(),
    )


def _request_messages(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [
        record.getMessage() for record in caplog.records if record.name == "app.request"
    ]


def test_fast_request_does_not_log(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="app.request"):
        response = client.get("/health")

    assert response.status_code == 200
    assert _request_messages(caplog) == []


def test_slow_request_logs_only_a_warning(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _freeze_elapsed_ms(monkeypatch, 6000)
    with caplog.at_level(logging.INFO, logger="app.request"):
        response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["X-Process-Time"] == "6.000000"
    messages = _request_messages(caplog)
    assert messages == [
        "slow request method=GET path=/health status=200 duration_ms=6000.0 "
        "threshold_ms=5000"
    ]
    assert any(
        record.name == "app.request" and record.levelno == logging.WARNING
        for record in caplog.records
    )


def test_request_at_the_slow_threshold_does_not_log(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _freeze_elapsed_ms(monkeypatch, settings.SLOW_REQUEST_THRESHOLD_MS)
    with caplog.at_level(logging.INFO, logger="app.request"):
        response = client.get("/health")

    assert response.status_code == 200
    assert _request_messages(caplog) == []


def test_slow_request_warning_uses_the_configured_threshold(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "SLOW_REQUEST_THRESHOLD_MS", 8000)
    _freeze_elapsed_ms(monkeypatch, 6000)
    with caplog.at_level(logging.INFO, logger="app.request"):
        response = client.get("/health")

    assert response.status_code == 200
    assert _request_messages(caplog) == []

    caplog.clear()
    monkeypatch.setattr(settings, "SLOW_REQUEST_THRESHOLD_MS", 1000)
    _freeze_elapsed_ms(monkeypatch, 1500)
    with caplog.at_level(logging.INFO, logger="app.request"):
        response = client.get("/health")

    assert response.status_code == 200
    assert _request_messages(caplog) == [
        "slow request method=GET path=/health status=200 duration_ms=1500.0 "
        "threshold_ms=1000"
    ]


def test_slow_failed_request_logs_only_a_warning(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = create_app()

    @app.get("/__slow_failure")
    def _boom() -> None:
        raise RuntimeError("boom")

    _freeze_elapsed_ms(monkeypatch, 6000)
    with TestClient(app, raise_server_exceptions=False) as client:
        with caplog.at_level(logging.INFO, logger="app.request"):
            response = client.get("/__slow_failure")

    assert response.status_code == 500
    assert _request_messages(caplog) == [
        "slow request method=GET path=/__slow_failure status=500 "
        "duration_ms=6000.0 threshold_ms=5000"
    ]
