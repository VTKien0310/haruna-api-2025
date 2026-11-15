from typing import Annotated, NoReturn

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core import AppException
from app.features.pto.data import (
    CreatePtoTransactionWriterDep,
    FindPtoBankByOwnerAndYearReaderDep,
    FindPtoTransactionsByEntryReaderDep,
    UpdatePtoBankBalancesWriterDep,
)
from app.features.pto.entities import (
    PtoAffectEntry,
    PtoTransactionCause,
    PtoTransactionType,
)
from app.features.pto.services import (
    CalculatePtoBalanceDeductionServiceDep,
    CalculatePtoBalanceRestorationServiceDep,
    GetOrCreatePtoBankServiceDep,
)


class ReconcilePtoForEntryService:
    def __init__(
        self,
        find_bank: FindPtoBankByOwnerAndYearReaderDep,
        find_transactions: FindPtoTransactionsByEntryReaderDep,
        update_bank: UpdatePtoBankBalancesWriterDep,
        create_transaction: CreatePtoTransactionWriterDep,
        get_or_create_bank: GetOrCreatePtoBankServiceDep,
        calculate_balance_deduction_service: CalculatePtoBalanceDeductionServiceDep,
        calculate_balance_restoration_service: CalculatePtoBalanceRestorationServiceDep,
    ) -> None:
        self.__find_bank = find_bank
        self.__find_transactions = find_transactions
        self.__update_bank = update_bank
        self.__create_transaction = create_transaction
        self.__get_or_create_bank = get_or_create_bank
        self.__calculate_balance_deduction_service = calculate_balance_deduction_service
        self.__calculate_balance_restoration_service = (
            calculate_balance_restoration_service
        )

    async def handle(
        self,
        db_session: AsyncSession,
        affect_entry: PtoAffectEntry,
        old_penalty: int,
        new_penalty: int,
        year: int,
    ) -> None:
        delta = new_penalty - old_penalty
        if delta == 0:
            return
        if affect_entry.entry_type is None:
            self.__conflict()
        bank = await self.__find_bank.handle(db_session, affect_entry.owner_id, year)
        transactions = await self.__find_transactions.handle(
            db_session, affect_entry.id
        )
        net_penalty = 0
        outstanding_excess = 0
        for transaction in transactions:
            if (
                bank is None
                or transaction.pto_bank_id != bank.id
                or transaction.value < 0
                or not 0 <= transaction.exceed_bank_value <= transaction.value
            ):
                self.__conflict()
            sign = 1 if transaction.type == PtoTransactionType.DECREASE else -1
            net_penalty += sign * transaction.value
            outstanding_excess += sign * transaction.exceed_bank_value
        if net_penalty != old_penalty or not 0 <= outstanding_excess <= old_penalty:
            self.__conflict()
        if bank is None:
            if delta < 0:
                self.__conflict()
            bank = await self.__get_or_create_bank.handle_with_session(
                db_session, affect_entry.owner_id, year
            )

        if delta > 0:
            updated_bank, excess = self.__calculate_balance_deduction_service.handle(
                bank, delta
            )
            transaction_type = PtoTransactionType.DECREASE
        else:
            excess = min(-delta, outstanding_excess)
            remaining = -delta - excess
            updated_bank, remaining = (
                self.__calculate_balance_restoration_service.handle(bank, remaining)
            )
            if remaining:
                self.__conflict()
            transaction_type = PtoTransactionType.INCREASE
        await self.__update_bank.handle(db_session, updated_bank)
        await self.__create_transaction.handle(
            db_session,
            pto_bank_id=bank.id,
            entry_id=affect_entry.id,
            cause=PtoTransactionCause.from_entry_update(affect_entry.entry_type),
            type=transaction_type,
            value=abs(delta),
            exceed_bank_value=excess,
        )

    @staticmethod
    def __conflict() -> NoReturn:
        raise AppException(
            status_code=409,
            code="pto_adjustment_conflict",
            message="PTO history or restoration capacity is inconsistent",
        )


ReconcilePtoForEntryServiceDep = Annotated[ReconcilePtoForEntryService, Depends()]
