import logging

from fastapi.testclient import TestClient


def test_get_health_returns_ok_without_authentication(
    client: TestClient, caplog: logging.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="app.request"):
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "content": {"status": "ok"}}
    elapsed = float(response.headers["X-Process-Time"])
    assert elapsed >= 0
    assert any(
        "method=GET" in message
        and "path=/health" in message
        and "status=200" in message
        for message in caplog.messages
    )
