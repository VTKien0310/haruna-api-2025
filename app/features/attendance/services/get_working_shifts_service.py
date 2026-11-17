from datetime import date
from typing import Annotated

from fastapi import Depends

from app.features.attendance.entities import (
    WorkdayException,
    WorkdayExceptionTime,
    WorkdayExceptionType,
)


class GetWorkingShiftsService:
    def handle(
        self, day: date, exceptions: list[WorkdayException]
    ) -> set[WorkdayExceptionTime]:
        working_shifts: set[WorkdayExceptionTime] = set()
        for shift in (WorkdayExceptionTime.MORNING, WorkdayExceptionTime.AFTERNOON):
            matching = [
                exception
                for exception in exceptions
                if exception.date == day
                and exception.time in (WorkdayExceptionTime.FULL_DAY, shift)
            ]
            if any(
                exception.type == WorkdayExceptionType.HOLIDAY for exception in matching
            ):
                continue
            if day.weekday() < 5 or any(
                exception.type == WorkdayExceptionType.WORKDAY for exception in matching
            ):
                working_shifts.add(shift)
        return working_shifts


GetWorkingShiftsServiceDep = Annotated[GetWorkingShiftsService, Depends()]
