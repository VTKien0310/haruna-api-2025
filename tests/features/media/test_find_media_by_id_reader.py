import sqlite3

from app.features.media.data import FindMediaByIdReader
from app.features.media.entities import MediaType
from tests.factories.records import insert_media
from tests.fakes.sqlite_supabase import SqliteSupabasePort


def test_find_media_by_id_returns_the_factory_row(
    database: sqlite3.Connection, supabase: SqliteSupabasePort
) -> None:
    insert_media(database, id="media-1", name="photo.jpg", type=int(MediaType.IMAGE))

    media = FindMediaByIdReader(supabase).handle("media-1")

    assert media is not None
    assert media.id == "media-1"
    assert media.name == "photo.jpg"
    assert media.type == MediaType.IMAGE
    assert media.storage_path == "media-1/photo.jpg"
    assert media.thumbnail_path is None


def test_find_media_by_id_sees_an_empty_database(
    supabase: SqliteSupabasePort,
) -> None:
    assert FindMediaByIdReader(supabase).handle("media-1") is None
