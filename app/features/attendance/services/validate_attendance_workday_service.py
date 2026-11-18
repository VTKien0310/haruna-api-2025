from datetime import date, time
from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core import AppException
from app.features.attendance.data import FindWorkdayExceptionsByDatesReaderDep
from app.features.attendance.entities import WorkdayExceptionTime
from app.features.attendance.services import GetWorkingShiftsServiceDep


class ValidateAttendanceWorkdayService:
    def __init__(
        self,
        reader: FindWorkdayExceptionsByDatesReaderDep,
        get_working_shifts_service: GetWorkingShiftsServiceDep,
    ) -> None:
        self.__reader = reader
        self.__get_working_shifts_service = get_working_shifts_service

    async def handle(
        self,
        session: AsyncSession,
        dates: list[date],
        period: WorkdayExceptionTime = WorkdayExceptionTime.FULL_DAY,
        *,
        interval: tuple[time, time] | None = None,
    ) -> None:
        periods = [WorkdayExceptionTime.MORNING, WorkdayExceptionTime.AFTERNOON]
        require_all = True
        if interval is not None:
            start, end = interval
            periods = [
                shift
                for shift, lower, upper in (
                    (WorkdayExceptionTime.MORNING, time(8), time(12)),
                    (WorkdayExceptionTime.AFTERNOON, time(13, 30), time(17, 30)),
                )
                if start < upper and lower < end
            ]
            if not periods:
                periods = [WorkdayExceptionTime.MORNING, WorkdayExceptionTime.AFTERNOON]
                require_all = False
        elif period != WorkdayExceptionTime.FULL_DAY:
            periods = [period]

        exceptions = await self.__reader.handle(session, dates)
        for day in dates:
            scheduled_shifts = self.__get_working_shifts_service.handle(day, exceptions)
            working = [shift in scheduled_shifts for shift in periods]
            if not (all(working) if require_all else any(working)):
                raise AppException(
                    status_code=409,
                    code="attendance_non_workday",
                    message="Attendance entry requires a working day and shift",
                )


ValidateAttendanceWorkdayServiceDep = Annotated[
    ValidateAttendanceWorkdayService, Depends()
]
