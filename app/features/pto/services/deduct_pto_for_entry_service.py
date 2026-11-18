from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.features.pto.entities import PtoAffectEntry, PtoTransaction
from app.features.pto.services.get_or_create_pto_bank_service import (
    GetOrCreatePtoBankServiceDep,
)
from app.features.pto.services.deduct_pto_from_bank_service import (
    DeductPtoFromBankServiceDep,
)


class DeductPtoForEntryService:
    def __init__(
        self,
        get_or_create_pto_bank_service: GetOrCreatePtoBankServiceDep,
        deduct_pto_from_bank_service: DeductPtoFromBankServiceDep,
    ) -> None:
        self.__get_or_create_pto_bank_service = get_or_create_pto_bank_service
        self.__deduct_pto_from_bank_service = deduct_pto_from_bank_service

    async def handle(
        self,
        db_session: AsyncSession,
        user_id: str,
        affect_entry: PtoAffectEntry,
        deduction_minutes: int,
        year: int,
    ) -> PtoTransaction | None:
        if affect_entry.no_deduction or deduction_minutes <= 0:
            return None
        if affect_entry.entry_type is None:
            return None

        bank = await self.__get_or_create_pto_bank_service.handle_with_session(
            db_session, user_id, year
        )
        result = await self.__deduct_pto_from_bank_service.handle(
            db_session, bank, affect_entry, deduction_minutes
        )
        return result[1] if result is not None else None


DeductPtoForEntryServiceDep = Annotated[DeductPtoForEntryService, Depends()]
