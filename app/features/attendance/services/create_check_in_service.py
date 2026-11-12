from datetime import date, time
from typing import Annotated

from fastapi import Depends, status

from app.core import AppException
from app.database import DbSessionManagerDep
from app.features.attendance.constants import WORK_START_MINUTES
from app.features.attendance.data import (
    CreateCheckInEntryWriterDep,
    FindCheckInEntryByIdsAndDateReaderDep,
)
from app.features.attendance.entities import CheckInEntry
from app.features.pto.data import (
    CreatePtoAffectEntryWriterDep,
    FindPtoAffectEntriesByOwnerAndTypeReaderDep,
)
from app.features.pto.entities import PtoAffectEntryType
from app.features.pto.services import DeductPtoForEntryServiceDep


class CreateCheckInService:
    def __init__(
        self,
        find_pto_affect_entries_reader: FindPtoAffectEntriesByOwnerAndTypeReaderDep,
        find_check_in_entry_reader: FindCheckInEntryByIdsAndDateReaderDep,
        create_check_in_entry_writer: CreateCheckInEntryWriterDep,
        create_pto_affect_entry_writer: CreatePtoAffectEntryWriterDep,
        deduct_pto_for_entry_service: DeductPtoForEntryServiceDep,
        db_session_manager: DbSessionManagerDep,
    ) -> None:
        self.__find_pto_affect_entries_reader = find_pto_affect_entries_reader
        self.__find_check_in_entry_reader = find_check_in_entry_reader
        self.__create_check_in_entry_writer = create_check_in_entry_writer
        self.__create_pto_affect_entry_writer = create_pto_affect_entry_writer
        self.__deduct_pto_for_entry_service = deduct_pto_for_entry_service
        self.__db_session_manager = db_session_manager

    async def handle(
        self,
        user_id: str,
        day: date,
        arrival: time,
        no_deduction: int | None = None,
        note: str | None = None,
    ) -> CheckInEntry:
        async with self.__db_session_manager.transaction() as db_session:
            arrival = arrival.replace(second=0, microsecond=0)

            affect_entries = await self.__find_pto_affect_entries_reader.handle(
                db_session, user_id, PtoAffectEntryType.CHECK_IN
            )
            entry_ids = [
                entry.entry_id for entry in affect_entries if entry.entry_id is not None
            ]
            existing = await self.__find_check_in_entry_reader.handle(
                db_session, entry_ids, day
            )
            if existing is not None:
                raise AppException(
                    status_code=status.HTTP_409_CONFLICT,
                    code="check_in_already_exists",
                    message=f"Check-in on '{day}' already exists",
                )

            check_in = await self.__create_check_in_entry_writer.handle(
                db_session, day, arrival
            )
            affect_entry = await self.__create_pto_affect_entry_writer.handle(
                db_session,
                owner_id=user_id,
                entry_id=check_in.id,
                entry_type=PtoAffectEntryType.CHECK_IN,
                no_deduction=no_deduction,
                note=note,
            )
            await self.__deduct_pto_for_entry_service.handle(
                db_session,
                user_id,
                affect_entry,
                self.__deduction_minutes(arrival),
                day.year,
            )

            return check_in

    @staticmethod
    def __deduction_minutes(arrival: time) -> int:
        arrival_minutes = arrival.hour * 60 + arrival.minute
        return max(arrival_minutes - WORK_START_MINUTES, 0)


CreateCheckInServiceDep = Annotated[CreateCheckInService, Depends()]
