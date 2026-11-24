import io
import sqlite3

from fastapi.testclient import TestClient
from PIL import Image

from tests.factories.records import insert_media
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


def test_create_thumbnail_returns_a_signed_url(
    client: TestClient, supabase: SqliteSupabasePort, database: sqlite3.Connection
) -> None:
    supabase.auth().register("token-1")
    insert_media(database)
    supabase.storage_media().upload("media-1/photo.jpg", _jpeg(40, 20))

    response = client.post(
        "/api/medias/media-1/thumbnails",
        json={"width": 16, "height": 8},
        headers={"Authorization": "Bearer token-1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert (
        body["content"]["thumbnail_signed_url"]
        == "https://storage.invalid/resized/media-1/16x8.jpeg?expires=1800"
    )


def _jpeg(width: int, height: int) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), "red").save(buffer, format="JPEG")
    return buffer.getvalue()
