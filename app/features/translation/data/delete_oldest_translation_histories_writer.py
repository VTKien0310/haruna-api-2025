from typing import Annotated

from fastapi import Depends

from app.ports.supabase import SupabasePortDep


class DeleteOldestTranslationHistoriesWriter:
    def __init__(self, supabase: SupabasePortDep) -> None:
        self.__supabase = supabase

    def handle(self, owner_id: str, keep_limit: int) -> int:
        result = (
            self.__supabase.table_translation_history()
            .select("id")
            .eq("owner_id", owner_id)
            .order("created_at")
            .execute()
        )

        rows = result.data or []
        excess = len(rows) - keep_limit + 1

        if excess <= 0:
            return 0

        ids_to_delete = [str(row["id"]) for row in rows[:excess]]

        self.__supabase.table_translation_history().delete().in_(
            "id", ids_to_delete
        ).eq("owner_id", owner_id).execute()

        return len(ids_to_delete)


DeleteOldestTranslationHistoriesWriterDep = Annotated[
    DeleteOldestTranslationHistoriesWriter, Depends()
]
