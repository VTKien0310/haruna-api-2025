from typing import Annotated

from fastapi import Depends

from app.features.profile.entities import Profile
from app.ports.supabase import SupabasePortDep


class FindProfileByUserIdReader:
    def __init__(self, supabase: SupabasePortDep) -> None:
        self.__supabase = supabase

    def handle(self, user_id: str) -> Profile | None:
        result = (
            self.__supabase.table_profile()
            .select()
            .eq("user_id", user_id)
            .single()
            .execute()
            .data
        )

        if result is None:
            return None

        return Profile.from_spb_data(result)


FindProfileByUserIdReaderDep = Annotated[FindProfileByUserIdReader, Depends()]
