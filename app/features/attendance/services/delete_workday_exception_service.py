from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core import AppException
from app.database import DbSessionManagerDep
from app.features.attendance.data import (
    DeleteWorkdayExceptionWriterDep,
    FindWorkdayExceptionReaderDep,
    LockAttendanceCalendarWriterDep,
)
from app.features.attendance.services import (
    GetWorkdayExceptionTodayServiceDep,
    RequireMutableWorkdayExceptionServiceDep,
)
from app.features.authorization.entities import SpecialPermission
from app.features.authorization.services import RequireSpecialPermissionServiceDep


class DeleteWorkdayExceptionService:
    def __init__(
        self,
        db_session_manager: DbSessionManagerDep,
        authorize: RequireSpecialPermissionServiceDep,
        reader: FindWorkdayExceptionReaderDep,
        delete: DeleteWorkdayExceptionWriterDep,
        get_today: GetWorkdayExceptionTodayServiceDep,
        require_mutable: RequireMutableWorkdayExceptionServiceDep,
        lock_calendar: LockAttendanceCalendarWriterDep,
    ) -> None:
        self.__get_today = get_today
        self.__require_mutable = require_mutable
        self.__lock_calendar = lock_calendar
        self.__db_session_manager = db_session_manager
        self.__authorize = authorize
        self.__reader = reader
        self.__delete = delete

    async def handle(self, user_id: str, exception_id: UUID) -> None:
        async with self.__db_session_manager.transaction() as session:
            await self.__authorize.handle(
                session, user_id, SpecialPermission.MANAGE_WORKDAY_EXCEPTIONS
            )
            await self.__lock_calendar.handle(session, exclusive=True)
            record = await self.__reader.handle(session, exception_id, for_update=True)
            if record is None:
                raise AppException(
                    status_code=404,
                    code="workday_exception_not_found",
                    message="Workday exception not found",
                )
            self.__require_mutable.handle(record.date, self.__get_today.handle())
            await self.__delete.handle(session, record)


DeleteWorkdayExceptionServiceDep = Annotated[DeleteWorkdayExceptionService, Depends()]
