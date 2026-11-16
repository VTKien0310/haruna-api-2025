from datetime import date
from typing import Annotated

from fastapi import Depends

from app.core import AppException
from app.features.attendance.entities import WorkdayExceptionType


class RequireValidWorkdayExceptionDayService:
    def handle(
        self, exception_date: date, exception_type: WorkdayExceptionType
    ) -> None:
        weekend = exception_date.weekday() >= 5
        if weekend != (exception_type == WorkdayExceptionType.WORKDAY):
            raise AppException(
                status_code=409,
                code="invalid_workday_exception_day",
                message="Holidays require Monday through Friday; workdays require Saturday or Sunday",
            )


RequireValidWorkdayExceptionDayServiceDep = Annotated[
    RequireValidWorkdayExceptionDayService, Depends()
]
