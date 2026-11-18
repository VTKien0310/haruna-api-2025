from datetime import date
from typing import Annotated

from fastapi import Depends, status

from app.core import AppException
from app.database import DbSessionManagerDep
from app.features.attendance.data import (
    CreateRemoteWorkEntryWriterDep,
    FindRemoteWorkEntriesByIdsAndDateReaderDep,
    LockAttendanceCalendarWriterDep,
)
from app.features.attendance.entities import (
    RemoteWorkEntry,
    RemoteWorkType,
    WorkdayExceptionTime,
)
from app.features.attendance.services import ValidateAttendanceWorkdayServiceDep
from app.features.pto.data import (
    CreatePtoAffectEntryWriterDep,
    FindPtoAffectEntriesByOwnerAndTypeReaderDep,
)
from app.features.pto.entities import PtoAffectEntryType


class CreateRemoteWorkService:
    def __init__(
        self,
        find_pto_affect_entries_reader: FindPtoAffectEntriesByOwnerAndTypeReaderDep,
        find_remote_work_entries_reader: FindRemoteWorkEntriesByIdsAndDateReaderDep,
        create_remote_work_entry_writer: CreateRemoteWorkEntryWriterDep,
        create_pto_affect_entry_writer: CreatePtoAffectEntryWriterDep,
        db_session_manager: DbSessionManagerDep,
        validate_workday: ValidateAttendanceWorkdayServiceDep,
        lock_calendar: LockAttendanceCalendarWriterDep,
    ) -> None:
        self.__find_pto_affect_entries_reader = find_pto_affect_entries_reader
        self.__find_remote_work_entries_reader = find_remote_work_entries_reader
        self.__create_remote_work_entry_writer = create_remote_work_entry_writer
        self.__create_pto_affect_entry_writer = create_pto_affect_entry_writer
        self.__validate_workday = validate_workday
        self.__lock_calendar = lock_calendar
        self.__db_session_manager = db_session_manager

    async def handle(
        self,
        user_id: str,
        day: date,
        entry_type: RemoteWorkType,
        note: str | None = None,
        title: str = "Untitled",
    ) -> RemoteWorkEntry:
        async with self.__db_session_manager.transaction() as db_session:
            await self.__lock_calendar.handle(db_session)
            await self.__validate_workday.handle(
                db_session, [day], WorkdayExceptionTime(entry_type)
            )
            affect_entries = await self.__find_pto_affect_entries_reader.handle(
                db_session, user_id, PtoAffectEntryType.REMOTE_WORK
            )
            entry_ids = [
                entry.entry_id for entry in affect_entries if entry.entry_id is not None
            ]
            existing_entries = await self.__find_remote_work_entries_reader.handle(
                db_session, entry_ids, day
            )
            if any(
                existing.type == RemoteWorkType.FULL_DAY
                or entry_type == RemoteWorkType.FULL_DAY
                or existing.type == entry_type
                for existing in existing_entries
            ):
                raise AppException(
                    status_code=status.HTTP_409_CONFLICT,
                    code="remote_work_already_exists",
                    message=f"Remote work on '{day}' already exists",
                )

            remote_work = await self.__create_remote_work_entry_writer.handle(
                db_session, day, entry_type
            )
            await self.__create_pto_affect_entry_writer.handle(
                db_session,
                owner_id=user_id,
                entry_id=remote_work.id,
                entry_type=PtoAffectEntryType.REMOTE_WORK,
                note=note,
                title=title,
            )

            return remote_work


CreateRemoteWorkServiceDep = Annotated[CreateRemoteWorkService, Depends()]
