from datetime import date
from typing import Annotated

from fastapi import Depends

from app.core import AppException


class RequireMutableWorkdayExceptionService:
    def handle(self, exception_date: date, today: date) -> None:
        if exception_date < today:
            raise AppException(
                status_code=409,
                code="past_workday_exception_immutable",
                message="Past workday exceptions cannot be changed",
            )


RequireMutableWorkdayExceptionServiceDep = Annotated[
    RequireMutableWorkdayExceptionService, Depends()
]
