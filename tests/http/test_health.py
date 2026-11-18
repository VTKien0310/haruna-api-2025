from fastapi.testclient import TestClient


def test_get_health_returns_ok_without_authentication(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "content": {"status": "ok"}}
