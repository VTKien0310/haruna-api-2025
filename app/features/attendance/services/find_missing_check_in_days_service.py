from datetime import date, timedelta
from typing import Annotated

from fastapi import Depends

from app.features.attendance.constants import MISS_CHECK_IN_COUNTING_START
from app.features.attendance.entities import (
    CheckInEntry,
    WorkdayException,
)
from app.features.attendance.types import AttendanceEntryWithAffect
from app.features.attendance.services import (
    CalculateMissCheckInPenaltyServiceDep,
    GetWorkingShiftsServiceDep,
)


class FindMissingCheckInDaysService:
    def __init__(
        self,
        get_working_shifts_service: GetWorkingShiftsServiceDep,
        calculate_miss_check_in_penalty_service: CalculateMissCheckInPenaltyServiceDep,
    ) -> None:
        self.__get_working_shifts_service = get_working_shifts_service
        self.__calculate_miss_check_in_penalty_service = (
            calculate_miss_check_in_penalty_service
        )

    def handle(
        self,
        start_date: date,
        end_date: date,
        entries: list[AttendanceEntryWithAffect],
        exceptions: list[WorkdayException],
    ) -> list[tuple[date, int]]:
        start_date = max(start_date, MISS_CHECK_IN_COUNTING_START)
        if start_date > end_date:
            return []

        entries_by_day: dict[date, list[AttendanceEntryWithAffect]] = {}
        for affect, entry in entries:
            entries_by_day.setdefault(entry.date, []).append((affect, entry))

        missing_days: list[tuple[date, int]] = []
        for offset in range((end_date - start_date).days + 1):
            day = start_date + timedelta(days=offset)
            day_entries = entries_by_day.get(day, [])
            if any(isinstance(entry, CheckInEntry) for _, entry in day_entries):
                continue

            scheduled_shifts = self.__get_working_shifts_service.handle(day, exceptions)
            if not scheduled_shifts:
                continue

            penalty = self.__calculate_miss_check_in_penalty_service.handle(
                scheduled_shifts, day_entries
            )
            if penalty > 0:
                missing_days.append((day, penalty))

        return missing_days


FindMissingCheckInDaysServiceDep = Annotated[FindMissingCheckInDaysService, Depends()]
