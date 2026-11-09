from datetime import date
from typing import Annotated

from fastapi import Depends, status

from app.core import AppException
from app.database import DbSessionManagerDep
from app.features.attendance.data import (
    CreateWorkTimeEntryWriterDep,
    FindWorkTimeEntriesByIdsAndDateReaderDep,
)
from app.features.attendance.entities import (
    WorkTimeEntry,
    WorkTimeShift,
    WorkTimeType,
)
from app.features.pto.constants import SHIFT_MINUTES
from app.features.pto.data import (
    CreatePtoAffectEntryWriterDep,
    FindPtoAffectEntriesByOwnerAndTypeReaderDep,
)
from app.features.pto.entities import PtoAffectEntryType


class CreateWorkTimeService:
    def __init__(
        self,
        find_pto_affect_entries_reader: FindPtoAffectEntriesByOwnerAndTypeReaderDep,
        find_work_time_entries_reader: FindWorkTimeEntriesByIdsAndDateReaderDep,
        create_work_time_entry_writer: CreateWorkTimeEntryWriterDep,
        create_pto_affect_entry_writer: CreatePtoAffectEntryWriterDep,
        db_session_manager: DbSessionManagerDep,
    ) -> None:
        self.__find_pto_affect_entries_reader = find_pto_affect_entries_reader
        self.__find_work_time_entries_reader = find_work_time_entries_reader
        self.__create_work_time_entry_writer = create_work_time_entry_writer
        self.__create_pto_affect_entry_writer = create_pto_affect_entry_writer
        self.__db_session_manager = db_session_manager

    async def handle(
        self,
        user_id: str,
        day: date,
        shift: WorkTimeShift,
        entry_type: WorkTimeType,
        duration: int,
    ) -> WorkTimeEntry:
        async with self.__db_session_manager.transaction() as db_session:
            affect_entries = await self.__find_pto_affect_entries_reader.handle(
                db_session, user_id, PtoAffectEntryType.WORK_TIME
            )
            entry_ids = [
                entry.entry_id for entry in affect_entries if entry.entry_id is not None
            ]
            existing_entries = await self.__find_work_time_entries_reader.handle(
                db_session, entry_ids, day
            )
            shift_entries = [entry for entry in existing_entries if entry.time == shift]
            if any(entry.type == entry_type for entry in shift_entries):
                raise AppException(
                    status_code=status.HTTP_409_CONFLICT,
                    code="work_time_already_exists",
                    message=f"Work time on '{day}' already exists",
                )
            if (
                sum(entry.duration for entry in shift_entries) + duration
                >= SHIFT_MINUTES
            ):
                raise AppException(
                    status_code=status.HTTP_409_CONFLICT,
                    code="work_time_overlaps",
                    message=f"Work time on '{day}' overlaps the whole shift",
                )

            work_time = await self.__create_work_time_entry_writer.handle(
                db_session, day, shift, entry_type, duration
            )
            await self.__create_pto_affect_entry_writer.handle(
                db_session,
                owner_id=user_id,
                entry_id=work_time.id,
                entry_type=PtoAffectEntryType.WORK_TIME,
            )

            return work_time


CreateWorkTimeServiceDep = Annotated[CreateWorkTimeService, Depends()]
