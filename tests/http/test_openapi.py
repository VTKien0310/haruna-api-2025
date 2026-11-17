import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import create_app
from app.core.config import settings
from app.core.response import apply_global_response_interface


def test_openapi_is_served_without_response_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "APP_ENABLE_DOCS", True)
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()
        assert schema["openapi"] == app.openapi_version
        assert "info" in schema
        assert schema["paths"]
        assert "ok" not in schema
        assert "content" not in schema
        assert client.get("/docs").status_code == 200
        assert client.get("/redoc").status_code == 200


def test_configured_openapi_url_is_served_without_response_envelope() -> None:
    app = FastAPI(openapi_url="/schema.json")
    apply_global_response_interface(app)
    with TestClient(app) as client:
        response = client.get("/schema.json")

    assert response.status_code == 200
    assert response.json()["openapi"] == app.openapi_version
    assert "ok" not in response.json()


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_documentation_routes_are_disabled(
    monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    monkeypatch.setattr(settings, "APP_ENABLE_DOCS", False)
    with TestClient(create_app()) as client:
        response = client.get(path)

    assert response.status_code == 404
    assert response.json()["ok"] is False
