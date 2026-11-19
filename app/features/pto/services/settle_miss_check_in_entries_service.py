from datetime import date, timedelta
from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.features.attendance.constants import MISS_CHECK_IN_COUNTING_START
from app.features.attendance.data import (
    CreateMissCheckInEntryWriterDep,
    FindMissCheckInEntriesByOwnerAndDateRangeReaderDep,
    FindOwnedPtoAttendanceEntriesByDateRangeReaderDep,
    FindWorkdayExceptionsByDatesReaderDep,
)
from app.features.attendance.services import FindMissingCheckInDaysServiceDep
from app.features.pto.entities import PtoAffectEntryType, PtoBank
from app.features.pto.data import CreatePtoAffectEntryWriterDep
from app.features.pto.services.deduct_pto_from_bank_service import (
    DeductPtoFromBankServiceDep,
)


class SettleMissCheckInEntriesService:
    def __init__(
        self,
        find_attendance_entries_reader: FindOwnedPtoAttendanceEntriesByDateRangeReaderDep,
        find_workday_exceptions_reader: FindWorkdayExceptionsByDatesReaderDep,
        find_miss_check_in_entries_reader: FindMissCheckInEntriesByOwnerAndDateRangeReaderDep,
        create_miss_check_in_entry_writer: CreateMissCheckInEntryWriterDep,
        create_pto_affect_entry_writer: CreatePtoAffectEntryWriterDep,
        deduct_pto_from_bank_service: DeductPtoFromBankServiceDep,
        find_missing_check_in_days_service: FindMissingCheckInDaysServiceDep,
    ) -> None:
        self.__find_attendance_entries_reader = find_attendance_entries_reader
        self.__find_workday_exceptions_reader = find_workday_exceptions_reader
        self.__find_miss_check_in_entries_reader = find_miss_check_in_entries_reader
        self.__create_miss_check_in_entry_writer = create_miss_check_in_entry_writer
        self.__create_pto_affect_entry_writer = create_pto_affect_entry_writer
        self.__deduct_pto_from_bank_service = deduct_pto_from_bank_service
        self.__find_missing_check_in_days_service = find_missing_check_in_days_service

    async def handle(
        self,
        session: AsyncSession,
        owner_id: str,
        bank: PtoBank,
        work_start_date: date,
    ) -> PtoBank:
        start_date = max(
            date(bank.year, 1, 1), work_start_date, MISS_CHECK_IN_COUNTING_START
        )
        end_date = date(bank.year, 12, 31)
        if start_date > end_date:
            return bank

        entries = await self.__find_attendance_entries_reader.handle(
            session, owner_id, start_date, end_date
        )
        days = [
            start_date + timedelta(days=offset)
            for offset in range((end_date - start_date).days + 1)
        ]
        exceptions = await self.__find_workday_exceptions_reader.handle(session, days)
        missed_days = self.__find_missing_check_in_days_service.handle(
            start_date, end_date, entries, exceptions
        )
        existing_entries = await self.__find_miss_check_in_entries_reader.handle(
            session, owner_id, start_date, end_date
        )
        existing_dates = {entry.date for entry in existing_entries}

        for day, penalty in missed_days:
            if day in existing_dates:
                continue
            missed_entry = await self.__create_miss_check_in_entry_writer.handle(
                session, day, penalty
            )
            affect_entry = await self.__create_pto_affect_entry_writer.handle(
                session,
                owner_id,
                missed_entry.id,
                PtoAffectEntryType.MISS_CHECK_IN,
                title=f"Missed check-in on {day.isoformat()}",
            )
            result = await self.__deduct_pto_from_bank_service.handle(
                session, bank, affect_entry, penalty
            )
            if result is not None:
                bank, _ = result
            existing_dates.add(day)

        return bank


SettleMissCheckInEntriesServiceDep = Annotated[
    SettleMissCheckInEntriesService, Depends()
]
