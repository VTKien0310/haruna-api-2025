from datetime import date, time
from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core import AppException
from app.features.attendance.data import FindWorkdayExceptionsByDatesReaderDep
from app.features.attendance.entities import WorkdayExceptionTime, WorkdayExceptionType


class ValidateAttendanceWorkdayService:
    def __init__(self, reader: FindWorkdayExceptionsByDatesReaderDep) -> None:
        self.__reader = reader

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
            working: list[bool] = []
            for shift in periods:
                matching = [
                    exception
                    for exception in exceptions
                    if exception.date == day
                    and exception.time in (WorkdayExceptionTime.FULL_DAY, shift)
                ]
                working.append(
                    not any(e.type == WorkdayExceptionType.HOLIDAY for e in matching)
                    and (
                        day.weekday() < 5
                        or any(e.type == WorkdayExceptionType.WORKDAY for e in matching)
                    )
                )
            if not (all(working) if require_all else any(working)):
                raise AppException(
                    status_code=409,
                    code="attendance_non_workday",
                    message="Attendance entry requires a working day and shift",
                )


ValidateAttendanceWorkdayServiceDep = Annotated[
    ValidateAttendanceWorkdayService, Depends()
]
