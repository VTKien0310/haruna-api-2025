from typing import Annotated

from fastapi import Depends

from app.features.pto.entities import PtoBank
from app.ports.supabase import SupabasePortDep


class CreatePtoBankWriter:
    def __init__(self, supabase: SupabasePortDep) -> None:
        self.__supabase = supabase

    def handle(
        self,
        owner_id: str,
        year: int,
        annual_balance: int,
        extended_balance: int,
        seniority_balance: int,
    ) -> PtoBank:
        result = (
            self.__supabase.table_pto_bank()
            .insert(
                {
                    "owner_id": owner_id,
                    "year": year,
                    "annual_balance": annual_balance,
                    "extended_balance": extended_balance,
                    "seniority_balance": seniority_balance,
                }
            )
            .execute()
            .data
        )

        return PtoBank.from_spb_data(result[0])


CreatePtoBankWriterDep = Annotated[CreatePtoBankWriter, Depends()]
