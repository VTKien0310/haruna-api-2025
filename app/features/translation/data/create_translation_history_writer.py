from typing import Annotated

from fastapi import Depends

from app.ports.supabase import SupabasePortDep


class CreateTranslationHistoryWriter:
    def __init__(self, supabase: SupabasePortDep) -> None:
        self.__supabase = supabase

    def handle(
        self,
        owner_id: str,
        source_language: str,
        target_language: str,
        source_text: str,
        translation: str,
    ) -> None:
        self.__supabase.table_translation_history().insert(
            {
                "owner_id": owner_id,
                "source_language": source_language,
                "target_language": target_language,
                "source_text": source_text,
                "translation": translation,
            }
        ).execute()


CreateTranslationHistoryWriterDep = Annotated[CreateTranslationHistoryWriter, Depends()]
