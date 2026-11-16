from dataclasses import replace
from datetime import time
from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core import AppException
from app.features.attendance.data import FindPtoAttendanceEntriesByDateReaderDep
from app.features.attendance.entities import (
    CheckInEntry,
    LeaveWorkEntry,
    RemoteWorkEntry,
    TimeOffEntry,
    WorkdayException,
    WorkdayExceptionTime,
    WorkTimeEntry,
    WorkTimeShift,
)
from app.features.pto.data import (
    FindPtoBankByOwnerAndYearReaderDep,
    FindPtoTransactionsByEntryReaderDep,
    LockPtoOwnerWriterDep,
    UpdatePtoAffectEntryWriterDep,
)
from app.features.pto.entities import PtoTransactionType
from app.features.pto.services import ReconcilePtoForEntryServiceDep


class RefundPtoForHolidayService:
    def __init__(
        self,
        find_bank: FindPtoBankByOwnerAndYearReaderDep,
        find_entries: FindPtoAttendanceEntriesByDateReaderDep,
        lock_owner: LockPtoOwnerWriterDep,
        find_transactions: FindPtoTransactionsByEntryReaderDep,
        update_affect: UpdatePtoAffectEntryWriterDep,
        reconcile: ReconcilePtoForEntryServiceDep,
    ) -> None:
        self.__find_bank = find_bank
        self.__find_entries = find_entries
        self.__lock_owner = lock_owner
        self.__find_transactions = find_transactions
        self.__update_affect = update_affect
        self.__reconcile = reconcile

    async def handle(self, session: AsyncSession, holiday: WorkdayException) -> None:
        entries = [
            (affect, entry)
            for affect, entry in await self.__find_entries.handle(session, holiday.date)
            if holiday.time == WorkdayExceptionTime.FULL_DAY
            or holiday.time in self.__periods(entry)
        ]
        for owner_id in sorted({affect.owner_id for affect, _ in entries}):
            await self.__lock_owner.handle(session, owner_id)
        for affect, _ in sorted(entries, key=lambda pair: pair[0].id):
            transactions = await self.__find_transactions.handle(session, affect.id)
            penalty = sum(
                transaction.value
                if transaction.type == PtoTransactionType.DECREASE
                else -transaction.value
                for transaction in transactions
            )
            if transactions and penalty == 0:
                bank = await self.__find_bank.handle(
                    session, affect.owner_id, holiday.date.year
                )
                if (
                    bank is None
                    or any(
                        transaction.pto_bank_id != bank.id
                        or transaction.value < 0
                        or not 0 <= transaction.exceed_bank_value <= transaction.value
                        for transaction in transactions
                    )
                    or sum(
                        transaction.exceed_bank_value
                        if transaction.type == PtoTransactionType.DECREASE
                        else -transaction.exceed_bank_value
                        for transaction in transactions
                    )
                    != 0
                ):
                    raise AppException(
                        status_code=409,
                        code="pto_adjustment_conflict",
                        message="PTO history or restoration capacity is inconsistent",
                    )
            if penalty < 0:
                raise AppException(
                    status_code=409,
                    code="pto_adjustment_conflict",
                    message="PTO history or restoration capacity is inconsistent",
                )
            updated = replace(affect, no_deduction=True)
            await self.__reconcile.handle(
                session, updated, penalty, 0, holiday.date.year
            )
            if not affect.no_deduction:
                await self.__update_affect.handle(session, updated)

    @staticmethod
    def __periods(
        entry: CheckInEntry
        | TimeOffEntry
        | RemoteWorkEntry
        | WorkTimeEntry
        | LeaveWorkEntry,
    ) -> tuple[WorkdayExceptionTime, ...]:
        morning = WorkdayExceptionTime.MORNING
        afternoon = WorkdayExceptionTime.AFTERNOON
        if isinstance(entry, CheckInEntry):
            return (morning,)
        if isinstance(entry, WorkTimeEntry):
            return (morning,) if entry.time == WorkTimeShift.MORNING else (afternoon,)
        if isinstance(entry, LeaveWorkEntry):
            periods = tuple(
                period
                for period, start, end in (
                    (morning, time(8), time(12)),
                    (afternoon, time(13, 30), time(17, 30)),
                )
                if entry.start < end and start < entry.end
            )
            return periods or (morning, afternoon)
        return (
            (morning, afternoon)
            if entry.type == 0
            else (WorkdayExceptionTime(entry.type),)
        )


RefundPtoForHolidayServiceDep = Annotated[RefundPtoForHolidayService, Depends()]
