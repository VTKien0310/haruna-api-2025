import sqlite3

from app.features.translation.data import (
    CreateTranslationHistoryWriter,
    DeleteOldestTranslationHistoriesWriter,
)
from tests.fakes.sqlite_supabase import SqliteSupabasePort


def test_create_translation_history_inserts_a_row(
    database: sqlite3.Connection, supabase: SqliteSupabasePort
) -> None:
    CreateTranslationHistoryWriter(supabase).handle(
        "user-1", "en", "ja", "hello", "こんにちは"
    )

    rows = database.execute(
        "SELECT owner_id, source_language, target_language, source_text, translation "
        "FROM translation_histories"
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["owner_id"] == "user-1"
    assert rows[0]["source_language"] == "en"
    assert rows[0]["target_language"] == "ja"
    assert rows[0]["source_text"] == "hello"
    assert rows[0]["translation"] == "こんにちは"


def test_delete_oldest_keeps_the_newest_history(
    database: sqlite3.Connection, supabase: SqliteSupabasePort
) -> None:
    writer = CreateTranslationHistoryWriter(supabase)
    writer.handle("user-1", "en", "ja", "one", "ichi")
    writer.handle("user-1", "en", "ja", "two", "ni")
    writer.handle("user-1", "en", "ja", "three", "san")
    writer.handle("user-2", "en", "ja", "other", "hoka")
    _stamp(database, "one", "2026-01-01T00:00:00")
    _stamp(database, "two", "2026-01-02T00:00:00")
    _stamp(database, "three", "2026-01-03T00:00:00")
    _stamp(database, "other", "2026-01-01T00:00:00")

    deleted = DeleteOldestTranslationHistoriesWriter(supabase).handle("user-1", 2)

    assert deleted == 2
    remaining = database.execute(
        "SELECT owner_id, source_text FROM translation_histories ORDER BY source_text"
    ).fetchall()
    assert [(row["owner_id"], row["source_text"]) for row in remaining] == [
        ("user-2", "other"),
        ("user-1", "three"),
    ]


def test_delete_oldest_leaves_rows_within_the_limit(
    database: sqlite3.Connection, supabase: SqliteSupabasePort
) -> None:
    CreateTranslationHistoryWriter(supabase).handle("user-1", "en", "ja", "one", "ichi")

    deleted = DeleteOldestTranslationHistoriesWriter(supabase).handle("user-1", 2)

    assert deleted == 0
    count = database.execute(
        "SELECT COUNT(*) AS total FROM translation_histories"
    ).fetchone()
    assert count is not None
    assert count["total"] == 1


def _stamp(connection: sqlite3.Connection, source_text: str, created_at: str) -> None:
    connection.execute(
        "UPDATE translation_histories SET created_at = ? WHERE source_text = ?",
        (created_at, source_text),
    )
    connection.commit()
