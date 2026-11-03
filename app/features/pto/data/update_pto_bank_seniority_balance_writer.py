from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends

from app.ports.supabase import SupabasePortDep


class UpdatePtoBankSeniorityBalanceWriter:
    def __init__(self, supabase: SupabasePortDep) -> None:
        self.__supabase = supabase

    def handle(self, bank_id: str, seniority_balance: int) -> None:
        self.__supabase.table_pto_bank().update(
            {
                "seniority_balance": seniority_balance,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", bank_id).execute()


UpdatePtoBankSeniorityBalanceWriterDep = Annotated[
    UpdatePtoBankSeniorityBalanceWriter, Depends()
]
