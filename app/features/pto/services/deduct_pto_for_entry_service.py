from dataclasses import replace
from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.features.pto.data import (
    CreatePtoTransactionWriterDep,
    UpdatePtoBankBalancesWriterDep,
)
from app.features.pto.entities import (
    PtoAffectEntry,
    PtoBank,
    PtoTransaction,
    PtoTransactionCause,
    PtoTransactionType,
)
from app.features.pto.services.get_or_create_pto_bank_service import (
    GetOrCreatePtoBankServiceDep,
)


class DeductPtoForEntryService:
    def __init__(
        self,
        get_or_create_pto_bank_service: GetOrCreatePtoBankServiceDep,
        create_pto_transaction_writer: CreatePtoTransactionWriterDep,
        update_pto_bank_balances_writer: UpdatePtoBankBalancesWriterDep,
    ) -> None:
        self.__get_or_create_pto_bank_service = get_or_create_pto_bank_service
        self.__create_pto_transaction_writer = create_pto_transaction_writer
        self.__update_pto_bank_balances_writer = update_pto_bank_balances_writer

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
        deducted_bank, exceed_bank_value = self.__deduct(bank, deduction_minutes)
        await self.__update_pto_bank_balances_writer.handle(db_session, deducted_bank)

        return await self.__create_pto_transaction_writer.handle(
            db_session,
            pto_bank_id=bank.id,
            entry_id=affect_entry.id,
            cause=PtoTransactionCause.from_entry_create(affect_entry.entry_type),
            type=PtoTransactionType.DECREASE,
            value=deduction_minutes,
            exceed_bank_value=exceed_bank_value,
        )

    @staticmethod
    def __deduct(bank: PtoBank, deduction_minutes: int) -> tuple[PtoBank, int]:
        remaining = deduction_minutes

        extended_balance = max(bank.extended_balance - remaining, 0)
        remaining -= bank.extended_balance - extended_balance

        seniority_balance = max(bank.seniority_balance - remaining, 0)
        remaining -= bank.seniority_balance - seniority_balance

        annual_balance = max(bank.annual_balance - remaining, 0)
        remaining -= bank.annual_balance - annual_balance

        deducted_bank = replace(
            bank,
            extended_balance=extended_balance,
            seniority_balance=seniority_balance,
            annual_balance=annual_balance,
        )
        return deducted_bank, remaining


DeductPtoForEntryServiceDep = Annotated[DeductPtoForEntryService, Depends()]
