import json
import sqlite3
from datetime import datetime, timezone

from app.features.authentication.entities import User
from app.features.translation.data import (
    CreateTranslationHistoryWriter,
    DeleteOldestTranslationHistoriesWriter,
)
from app.features.translation.services import ListLanguagesService, TranslateService
from tests.fakes.ai import AiApiFake
from tests.fakes.sqlite_supabase import SqliteSupabasePort


async def test_translate_service_stores_history(
    database: sqlite3.Connection, supabase: SqliteSupabasePort
) -> None:
    ai = AiApiFake()
    ai.queue_chat_completion(
        {
            "choices": [
                {"message": {"content": json.dumps({"translated_text": "こんにちは"})}}
            ]
        }
    )
    service = TranslateService(
        ai,
        ListLanguagesService(),
        CreateTranslationHistoryWriter(supabase),
        DeleteOldestTranslationHistoriesWriter(supabase),
    )
    user = User(
        id="user-1",
        aud="authenticated",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    translated = await service.handle(user, "hello", "en", "ja")

    assert translated == "こんにちは"
    rows = database.execute(
        "SELECT owner_id, source_text, translation FROM translation_histories"
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["owner_id"] == "user-1"
    assert rows[0]["source_text"] == "hello"
    assert rows[0]["translation"] == "こんにちは"
