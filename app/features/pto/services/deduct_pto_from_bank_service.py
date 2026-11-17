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
from app.features.pto.services.calculate_pto_balance_deduction_service import (
    CalculatePtoBalanceDeductionServiceDep,
)


class DeductPtoFromBankService:
    def __init__(
        self,
        create_pto_transaction_writer: CreatePtoTransactionWriterDep,
        update_pto_bank_balances_writer: UpdatePtoBankBalancesWriterDep,
        calculate_balance_deduction_service: CalculatePtoBalanceDeductionServiceDep,
    ) -> None:
        self.__create_pto_transaction_writer = create_pto_transaction_writer
        self.__update_pto_bank_balances_writer = update_pto_bank_balances_writer
        self.__calculate_balance_deduction_service = calculate_balance_deduction_service

    async def handle(
        self,
        db_session: AsyncSession,
        bank: PtoBank,
        affect_entry: PtoAffectEntry,
        deduction_minutes: int,
    ) -> tuple[PtoBank, PtoTransaction] | None:
        if affect_entry.no_deduction or deduction_minutes <= 0:
            return None
        if affect_entry.entry_type is None:
            return None

        deducted_bank, exceed_bank_value = (
            self.__calculate_balance_deduction_service.handle(bank, deduction_minutes)
        )
        await self.__update_pto_bank_balances_writer.handle(db_session, deducted_bank)
        transaction = await self.__create_pto_transaction_writer.handle(
            db_session,
            pto_bank_id=bank.id,
            entry_id=affect_entry.id,
            cause=PtoTransactionCause.from_entry_create(affect_entry.entry_type),
            type=PtoTransactionType.DECREASE,
            value=deduction_minutes,
            exceed_bank_value=exceed_bank_value,
        )
        return deducted_bank, transaction


DeductPtoFromBankServiceDep = Annotated[DeductPtoFromBankService, Depends()]
