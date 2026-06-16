from typing import Annotated

from fastapi import Depends

from app.ports import SupabasePortDep


class TranslationHistoryReader:
    def __init__(self, supabase: SupabasePortDep) -> None:
        self.__supabase = supabase

    def handle(self, user_id: str) -> None:
        pass


TranslationHistoryReaderDep = Annotated[TranslationHistoryReader, Depends()]
