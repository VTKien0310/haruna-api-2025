from dataclasses import replace
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core import AppException
from app.database import DbSessionManagerDep
from app.features.attendance.data import (
    FindOwnedWorkTimeEntryReaderDep,
    FindWorkTimeEntriesByIdsAndDateReaderDep,
    UpdateWorkTimeEntryWriterDep,
)
from app.features.attendance.entities import WorkTimeEntry
from app.features.attendance.requests import (
    CreateWorkTimeRequest,
    UpdateWorkTimeRequest,
)
from app.features.pto.constants import SHIFT_MINUTES
from app.features.pto.data import (
    FindPtoAffectEntriesByOwnerAndTypeReaderDep,
    UpdatePtoAffectEntryWriterDep,
)
from app.features.pto.entities import PtoAffectEntryType
from app.features.pto.services import ReconcilePtoForEntryServiceDep


class UpdateWorkTimeService:
    def __init__(
        self,
        find_owned: FindOwnedWorkTimeEntryReaderDep,
        update_entry: UpdateWorkTimeEntryWriterDep,
        find_conflicts: FindWorkTimeEntriesByIdsAndDateReaderDep,
        find_affect_entries: FindPtoAffectEntriesByOwnerAndTypeReaderDep,
        update_affect: UpdatePtoAffectEntryWriterDep,
        reconcile: ReconcilePtoForEntryServiceDep,
        db_session_manager: DbSessionManagerDep,
    ) -> None:
        self.__find_owned = find_owned
        self.__update_entry = update_entry
        self.__find_conflicts = find_conflicts
        self.__find_affect_entries = find_affect_entries
        self.__update_affect = update_affect
        self.__reconcile = reconcile
        self.__db_session_manager = db_session_manager

    async def handle(
        self, user_id: str, entry_id: UUID, request: UpdateWorkTimeRequest
    ) -> WorkTimeEntry:
        async with self.__db_session_manager.transaction() as session:
            owned = await self.__find_owned.handle(session, user_id, entry_id)
            if owned is None:
                raise AppException(
                    status_code=404,
                    code="attendance_entry_not_found",
                    message="Attendance entry not found",
                )
            entry, affect = owned
            if entry.date.year < date.today().year:
                self.__conflict("past_year_entry_not_editable")
            updated = self.__merge(entry, request)
            if updated.date.year != entry.date.year:
                raise RequestValidationError(
                    [
                        {
                            "loc": ("body", "date"),
                            "type": "value_error",
                            "msg": "Date must remain within the original year",
                        }
                    ]
                )
            await self.__check_conflicts(session, user_id, updated)
            updated_affect = replace(
                affect,
                title=request.title if request.title is not None else affect.title,
                no_deduction=bool(request.no_deduction)
                if "no_deduction" in request.model_fields_set
                else affect.no_deduction,
                note=(request.note or "")
                if "note" in request.model_fields_set
                else affect.note,
            )
            old_penalty = 0 if affect.no_deduction else entry.duration
            new_penalty = 0 if updated_affect.no_deduction else updated.duration
            await self.__update_entry.handle(session, updated)
            await self.__update_affect.handle(session, updated_affect)
            await self.__reconcile.handle(
                session, updated_affect, old_penalty, new_penalty, entry.date.year
            )
            return updated

    @staticmethod
    def __merge(entry: WorkTimeEntry, request: UpdateWorkTimeRequest) -> WorkTimeEntry:
        payload = {
            "date": entry.date,
            "time": entry.time,
            "type": entry.type,
            "duration": entry.duration,
        }
        payload.update(
            {
                key: value
                for key, value in request.model_dump(exclude_unset=True).items()
                if key not in {"note", "no_deduction", "title"}
            }
        )
        try:
            values = CreateWorkTimeRequest.model_validate(payload)
        except ValidationError as error:
            raise RequestValidationError(
                [
                    {**detail, "loc": ("body", *detail["loc"])}
                    for detail in error.errors()
                ]
            ) from error
        return WorkTimeEntry(
            id=entry.id,
            date=values.date,
            time=values.time,
            type=values.type,
            duration=values.duration,
        )

    async def __check_conflicts(
        self, session: AsyncSession, user_id: str, updated: WorkTimeEntry
    ) -> None:
        affects = await self.__find_affect_entries.handle(
            session, user_id, PtoAffectEntryType.WORK_TIME
        )
        ids = [
            a.entry_id
            for a in affects
            if a.entry_id is not None and a.entry_id != updated.id
        ]
        existing = await self.__find_conflicts.handle(session, ids, updated.date)
        shift_entries = [e for e in existing if e.time == updated.time]
        if any(e.type == updated.type for e in shift_entries):
            self.__conflict("work_time_already_exists")
        if sum(e.duration for e in shift_entries) + updated.duration >= SHIFT_MINUTES:
            self.__conflict("work_time_overlaps")

    @staticmethod
    def __conflict(code: str) -> None:
        raise AppException(
            status_code=409,
            code=code,
            message="Attendance update conflicts with existing records or year restrictions",
        )


UpdateWorkTimeServiceDep = Annotated[UpdateWorkTimeService, Depends()]
