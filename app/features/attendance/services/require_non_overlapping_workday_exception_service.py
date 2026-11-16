from datetime import date
from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core import AppException
from app.features.attendance.data import FindWorkdayExceptionsByDatesReaderDep
from app.features.attendance.entities import WorkdayExceptionTime, WorkdayExceptionType


class RequireNonOverlappingWorkdayExceptionService:
    def __init__(self, reader: FindWorkdayExceptionsByDatesReaderDep) -> None:
        self.__reader = reader

    async def handle(
        self,
        session: AsyncSession,
        day: date,
        exception_type: WorkdayExceptionType,
        period: WorkdayExceptionTime,
    ) -> None:
        existing = await self.__reader.handle(session, [day])
        if any(
            entry.type != exception_type
            or entry.time == WorkdayExceptionTime.FULL_DAY
            or period == WorkdayExceptionTime.FULL_DAY
            or entry.time == period
            for entry in existing
        ):
            raise AppException(
                status_code=409,
                code="workday_exception_overlap",
                message="Workday exception conflicts with an existing exception on that date",
            )


RequireNonOverlappingWorkdayExceptionServiceDep = Annotated[
    RequireNonOverlappingWorkdayExceptionService, Depends()
]
