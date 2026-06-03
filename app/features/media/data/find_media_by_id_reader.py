from typing import Annotated
from fastapi import Depends
from app.ports import SupabasePortDep
from app.features.media.entities import Media


class FindMediaByIdReader:
    def __init__(self, supabase: SupabasePortDep) -> None:
        self.__supabase = supabase

    def handle(self, media_id: str) -> Media | None:
        result = (
            self.__supabase.table_media()
            .select()
            .eq("id", media_id)
            .single()
            .execute()
            .data
        )

        if result is None:
            return None

        return Media.from_spb_data(result)


FindMediaByIdReaderDep = Annotated[FindMediaByIdReader, Depends()]
