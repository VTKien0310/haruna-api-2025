from typing import Annotated

from fastapi import Depends

from app.features.pto.entities import PtoBank
from app.ports.supabase import SupabasePortDep


class FindPtoBankByOwnerAndYearReader:
    def __init__(self, supabase: SupabasePortDep) -> None:
        self.__supabase = supabase

    def handle(self, owner_id: str, year: int) -> PtoBank | None:
        result = (
            self.__supabase.table_pto_bank()
            .select()
            .eq("owner_id", owner_id)
            .eq("year", year)
            .single()
            .execute()
            .data
        )

        if result is None:
            return None

        return PtoBank.from_spb_data(result)


FindPtoBankByOwnerAndYearReaderDep = Annotated[
    FindPtoBankByOwnerAndYearReader, Depends()
]
