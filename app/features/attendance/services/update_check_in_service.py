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
    FindCheckInEntryByIdsAndDateReaderDep,
    FindOwnedCheckInEntryReaderDep,
    LockAttendanceCalendarWriterDep,
    UpdateCheckInEntryWriterDep,
)
from app.features.attendance.entities import CheckInEntry, WorkdayExceptionTime
from app.features.attendance.requests import CreateCheckInRequest, UpdateCheckInRequest
from app.features.attendance.services import (
    CalculateCheckInPenaltyServiceDep,
    ValidateAttendanceWorkdayServiceDep,
)
from app.features.pto.data import (
    FindPtoAffectEntriesByOwnerAndTypeReaderDep,
    UpdatePtoAffectEntryWriterDep,
)
from app.features.pto.entities import PtoAffectEntryType
from app.features.pto.services import ReconcilePtoForEntryServiceDep


class UpdateCheckInService:
    def __init__(
        self,
        find_owned: FindOwnedCheckInEntryReaderDep,
        update_entry: UpdateCheckInEntryWriterDep,
        find_conflicts: FindCheckInEntryByIdsAndDateReaderDep,
        find_affect_entries: FindPtoAffectEntriesByOwnerAndTypeReaderDep,
        update_affect: UpdatePtoAffectEntryWriterDep,
        reconcile: ReconcilePtoForEntryServiceDep,
        db_session_manager: DbSessionManagerDep,
        calculate_penalty_service: CalculateCheckInPenaltyServiceDep,
        validate_workday: ValidateAttendanceWorkdayServiceDep,
        lock_calendar: LockAttendanceCalendarWriterDep,
    ) -> None:
        self.__find_owned = find_owned
        self.__update_entry = update_entry
        self.__find_conflicts = find_conflicts
        self.__find_affect_entries = find_affect_entries
        self.__update_affect = update_affect
        self.__reconcile = reconcile
        self.__validate_workday = validate_workday
        self.__lock_calendar = lock_calendar
        self.__db_session_manager = db_session_manager
        self.__calculate_penalty_service = calculate_penalty_service

    async def handle(
        self, user_id: str, entry_id: UUID, request: UpdateCheckInRequest
    ) -> CheckInEntry:
        async with self.__db_session_manager.transaction() as session:
            await self.__lock_calendar.handle(session)
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
            await self.__validate_workday.handle(
                session, [updated.date], WorkdayExceptionTime.MORNING
            )
            await self.__check_conflicts(session, user_id, updated)
            updated_affect = replace(
                affect,
                title=f"Check-in on {updated.date.isoformat()}",
                no_deduction=bool(request.no_deduction)
                if "no_deduction" in request.model_fields_set
                else affect.no_deduction,
                note=(request.note or "")
                if "note" in request.model_fields_set
                else affect.note,
            )
            old_penalty = (
                0
                if affect.no_deduction
                else self.__calculate_penalty_service.handle(entry.time)
            )
            new_penalty = (
                0
                if updated_affect.no_deduction
                else self.__calculate_penalty_service.handle(updated.time)
            )
            await self.__update_entry.handle(session, updated)
            await self.__update_affect.handle(session, updated_affect)
            await self.__reconcile.handle(
                session, updated_affect, old_penalty, new_penalty, entry.date.year
            )
            return updated

    @staticmethod
    def __merge(entry: CheckInEntry, request: UpdateCheckInRequest) -> CheckInEntry:
        payload = {"date": entry.date, "time": entry.time}
        payload.update(
            {
                key: value
                for key, value in request.model_dump(exclude_unset=True).items()
                if key not in {"note", "no_deduction"}
            }
        )
        try:
            values = CreateCheckInRequest.model_validate(payload)
        except ValidationError as error:
            raise RequestValidationError(
                [
                    {**detail, "loc": ("body", *detail["loc"])}
                    for detail in error.errors()
                ]
            ) from error
        return CheckInEntry(
            id=entry.id,
            date=values.date,
            time=values.time.replace(second=0, microsecond=0),
        )

    async def __check_conflicts(
        self, session: AsyncSession, user_id: str, updated: CheckInEntry
    ) -> None:
        affects = await self.__find_affect_entries.handle(
            session, user_id, PtoAffectEntryType.CHECK_IN
        )
        ids = [
            a.entry_id
            for a in affects
            if a.entry_id is not None and a.entry_id != updated.id
        ]
        existing = await self.__find_conflicts.handle(session, ids, updated.date)
        if existing is not None:
            self.__conflict("check_in_already_exists")

    @staticmethod
    def __conflict(code: str) -> None:
        raise AppException(
            status_code=409,
            code=code,
            message="Attendance update conflicts with existing records or year restrictions",
        )


UpdateCheckInServiceDep = Annotated[UpdateCheckInService, Depends()]
