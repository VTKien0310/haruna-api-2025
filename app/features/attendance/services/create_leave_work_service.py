from datetime import date, time
from typing import Annotated

from fastapi import Depends, status

from app.core import AppException
from app.database import DbSessionManagerDep
from app.features.attendance.data import (
    CreateLeaveWorkEntryWriterDep,
    FindLeaveWorkEntriesByIdsAndDateReaderDep,
)
from app.features.attendance.entities import LeaveWorkEntry
from app.features.pto.data import (
    CreatePtoAffectEntryWriterDep,
    FindPtoAffectEntriesByOwnerAndTypeReaderDep,
)
from app.features.pto.entities import PtoAffectEntryType
from app.features.pto.services import DeductPtoForEntryServiceDep


class CreateLeaveWorkService:
    def __init__(
        self,
        find_pto_affect_entries_reader: FindPtoAffectEntriesByOwnerAndTypeReaderDep,
        find_leave_work_entries_reader: FindLeaveWorkEntriesByIdsAndDateReaderDep,
        create_leave_work_entry_writer: CreateLeaveWorkEntryWriterDep,
        create_pto_affect_entry_writer: CreatePtoAffectEntryWriterDep,
        deduct_pto_for_entry_service: DeductPtoForEntryServiceDep,
        db_session_manager: DbSessionManagerDep,
    ) -> None:
        self.__find_pto_affect_entries_reader = find_pto_affect_entries_reader
        self.__find_leave_work_entries_reader = find_leave_work_entries_reader
        self.__create_leave_work_entry_writer = create_leave_work_entry_writer
        self.__create_pto_affect_entry_writer = create_pto_affect_entry_writer
        self.__deduct_pto_for_entry_service = deduct_pto_for_entry_service
        self.__db_session_manager = db_session_manager

    async def handle(
        self,
        user_id: str,
        day: date,
        start: time,
        end: time,
        no_deduction: int | None = None,
        note: str | None = None,
    ) -> LeaveWorkEntry:
        async with self.__db_session_manager.transaction() as db_session:
            affect_entries = await self.__find_pto_affect_entries_reader.handle(
                db_session, user_id, PtoAffectEntryType.LEAVE_WORK
            )
            entry_ids = [
                entry.entry_id for entry in affect_entries if entry.entry_id is not None
            ]
            existing_entries = await self.__find_leave_work_entries_reader.handle(
                db_session, entry_ids, day
            )
            if any(
                start < existing.end and existing.start < end
                for existing in existing_entries
            ):
                raise AppException(
                    status_code=status.HTTP_409_CONFLICT,
                    code="leave_work_overlaps",
                    message=f"Leave work on '{day}' overlaps an existing interval",
                )

            leave_work = await self.__create_leave_work_entry_writer.handle(
                db_session, day, start, end
            )
            affect_entry = await self.__create_pto_affect_entry_writer.handle(
                db_session,
                owner_id=user_id,
                entry_id=leave_work.id,
                entry_type=PtoAffectEntryType.LEAVE_WORK,
                no_deduction=no_deduction,
                note=note,
            )
            await self.__deduct_pto_for_entry_service.handle(
                db_session,
                user_id,
                affect_entry,
                self.__deduction_minutes(start, end),
                day.year,
            )

            return leave_work

    @staticmethod
    def __deduction_minutes(start: time, end: time) -> int:
        start_minutes = start.hour * 60 + start.minute
        end_minutes = end.hour * 60 + end.minute
        return max(end_minutes - start_minutes, 0)


CreateLeaveWorkServiceDep = Annotated[CreateLeaveWorkService, Depends()]
