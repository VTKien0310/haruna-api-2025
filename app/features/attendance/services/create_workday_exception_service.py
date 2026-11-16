from typing import Annotated

from fastapi import Depends

from app.database import DbSessionManagerDep, WorkdayExceptionRecord
from app.features.attendance.data import (
    LockAttendanceCalendarWriterDep,
    SaveWorkdayExceptionWriterDep,
)
from app.features.attendance.entities import WorkdayException, WorkdayExceptionType
from app.features.attendance.requests import CreateWorkdayExceptionRequest
from app.features.attendance.services import (
    GetWorkdayExceptionTodayServiceDep,
    RefundPtoForHolidayServiceDep,
    RequireMutableWorkdayExceptionServiceDep,
    RequireNonOverlappingWorkdayExceptionServiceDep,
    RequireValidWorkdayExceptionDayServiceDep,
)
from app.features.authorization.entities import SpecialPermission
from app.features.authorization.services import RequireSpecialPermissionServiceDep


class CreateWorkdayExceptionService:
    def __init__(
        self,
        db_session_manager: DbSessionManagerDep,
        authorize: RequireSpecialPermissionServiceDep,
        save: SaveWorkdayExceptionWriterDep,
        get_today: GetWorkdayExceptionTodayServiceDep,
        require_mutable: RequireMutableWorkdayExceptionServiceDep,
        require_valid_day: RequireValidWorkdayExceptionDayServiceDep,
        refund_holiday: RefundPtoForHolidayServiceDep,
        lock_calendar: LockAttendanceCalendarWriterDep,
        require_non_overlapping: RequireNonOverlappingWorkdayExceptionServiceDep,
    ) -> None:
        self.__require_non_overlapping = require_non_overlapping
        self.__get_today = get_today
        self.__require_mutable = require_mutable
        self.__require_valid_day = require_valid_day
        self.__refund_holiday = refund_holiday
        self.__lock_calendar = lock_calendar
        self.__db_session_manager = db_session_manager
        self.__authorize = authorize
        self.__save = save

    async def handle(
        self, user_id: str, request: CreateWorkdayExceptionRequest
    ) -> WorkdayException:
        async with self.__db_session_manager.transaction() as session:
            await self.__authorize.handle(
                session, user_id, SpecialPermission.MANAGE_WORKDAY_EXCEPTIONS
            )
            await self.__lock_calendar.handle(session, exclusive=True)
            today = self.__get_today.handle()
            self.__require_mutable.handle(request.date, today)
            self.__require_valid_day.handle(request.date, request.type)
            await self.__require_non_overlapping.handle(
                session, request.date, request.type, request.time
            )
            record = WorkdayExceptionRecord(
                type=int(request.type),
                date=request.date,
                time=int(request.time),
                title=request.title,
            )
            exception = await self.__save.handle(session, record)
            if exception.type == WorkdayExceptionType.HOLIDAY:
                await self.__refund_holiday.handle(session, exception)
            return exception


CreateWorkdayExceptionServiceDep = Annotated[CreateWorkdayExceptionService, Depends()]
