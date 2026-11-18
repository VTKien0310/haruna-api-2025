from fastapi.testclient import TestClient

from tests.fakes.sqlite_supabase import SqliteSupabasePort


def test_create_thumbnail_rejects_a_missing_token(client: TestClient) -> None:
    response = client.post(
        "/api/medias/media-1/thumbnails",
        json={"width": 8, "height": 8},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["ok"] is False
    assert body["content"]["error"]["code"] == "unauthorized"


def test_create_thumbnail_reports_missing_media(
    client: TestClient, supabase: SqliteSupabasePort
) -> None:
    supabase.auth().register("token-1")

    response = client.post(
        "/api/medias/missing/thumbnails",
        json={"width": 8, "height": 8},
        headers={"Authorization": "Bearer token-1"},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["ok"] is False
    assert body["content"]["error"]["code"] == "media_not_found"
