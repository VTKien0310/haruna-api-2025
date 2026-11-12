from datetime import date, timedelta
from typing import Annotated

from fastapi import Depends, status

from app.core import AppException
from app.database import DbSessionManagerDep
from app.features.attendance.data import (
    CreateTimeOffEntryWriterDep,
    FindTimeOffEntriesByIdsAndDatesReaderDep,
)
from app.features.attendance.entities import TimeOffEntry, TimeOffType
from app.features.pto.data import (
    CreatePtoAffectEntryWriterDep,
    FindPtoAffectEntriesByOwnerAndTypeReaderDep,
)
from app.features.pto.entities import PtoAffectEntryType


class CreateTimeOffService:
    def __init__(
        self,
        find_pto_affect_entries_reader: FindPtoAffectEntriesByOwnerAndTypeReaderDep,
        find_time_off_entries_reader: FindTimeOffEntriesByIdsAndDatesReaderDep,
        create_time_off_entry_writer: CreateTimeOffEntryWriterDep,
        create_pto_affect_entry_writer: CreatePtoAffectEntryWriterDep,
        db_session_manager: DbSessionManagerDep,
    ) -> None:
        self.__find_pto_affect_entries_reader = find_pto_affect_entries_reader
        self.__find_time_off_entries_reader = find_time_off_entries_reader
        self.__create_time_off_entry_writer = create_time_off_entry_writer
        self.__create_pto_affect_entry_writer = create_pto_affect_entry_writer
        self.__db_session_manager = db_session_manager

    async def handle(
        self,
        user_id: str,
        start_date: date,
        end_date: date | None,
        entry_type: TimeOffType,
        no_deduction: int | None = None,
        note: str | None = None,
    ) -> list[TimeOffEntry]:
        end_date = end_date or start_date
        days = [
            start_date + timedelta(days=offset)
            for offset in range((end_date - start_date).days + 1)
        ]

        async with self.__db_session_manager.transaction() as db_session:
            affect_entries = await self.__find_pto_affect_entries_reader.handle(
                db_session, user_id, PtoAffectEntryType.TIME_OFF
            )
            entry_ids = [
                entry.entry_id for entry in affect_entries if entry.entry_id is not None
            ]
            existing_entries = await self.__find_time_off_entries_reader.handle(
                db_session, entry_ids, days
            )
            existing_by_day: dict[date, list[TimeOffEntry]] = {}
            for entry in existing_entries:
                existing_by_day.setdefault(entry.date, []).append(entry)

            for day in days:
                if any(
                    existing.type == TimeOffType.FULL_DAY
                    or entry_type == TimeOffType.FULL_DAY
                    or existing.type == entry_type
                    for existing in existing_by_day.get(day, [])
                ):
                    raise AppException(
                        status_code=status.HTTP_409_CONFLICT,
                        code="time_off_already_exists",
                        message=f"Time off on '{day}' already exists",
                    )

            entries: list[TimeOffEntry] = []
            for day in days:
                entry = await self.__create_time_off_entry_writer.handle(
                    db_session, day, entry_type
                )
                await self.__create_pto_affect_entry_writer.handle(
                    db_session,
                    owner_id=user_id,
                    entry_id=entry.id,
                    entry_type=PtoAffectEntryType.TIME_OFF,
                    no_deduction=no_deduction,
                    note=note,
                )
                entries.append(entry)

            return entries


CreateTimeOffServiceDep = Annotated[CreateTimeOffService, Depends()]
