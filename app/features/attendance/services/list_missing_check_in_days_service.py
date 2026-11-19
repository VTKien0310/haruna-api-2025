from datetime import date, timedelta
from typing import Annotated

from fastapi import Depends, status

from app.core import AppException
from app.database import DbSessionManagerDep
from app.features.attendance.constants import MISS_CHECK_IN_COUNTING_START
from app.features.attendance.data import (
    FindOwnedPtoAttendanceEntriesByDateRangeReaderDep,
    FindWorkdayExceptionsByDatesReaderDep,
)
from app.features.attendance.services import (
    FindMissingCheckInDaysServiceDep,
)
from app.features.profile.data import FindProfileByUserIdReaderDep


class ListMissingCheckInDaysService:
    def __init__(
        self,
        find_profile_reader: FindProfileByUserIdReaderDep,
        find_attendance_entries_reader: FindOwnedPtoAttendanceEntriesByDateRangeReaderDep,
        find_workday_exceptions_reader: FindWorkdayExceptionsByDatesReaderDep,
        db_session_manager: DbSessionManagerDep,
        find_missing_check_in_days_service: FindMissingCheckInDaysServiceDep,
    ) -> None:
        self.__find_profile_reader = find_profile_reader
        self.__find_attendance_entries_reader = find_attendance_entries_reader
        self.__find_workday_exceptions_reader = find_workday_exceptions_reader
        self.__db_session_manager = db_session_manager
        self.__find_missing_check_in_days_service = find_missing_check_in_days_service

    async def handle(self, user_id: str) -> list[date]:
        today = date.today()
        start_date = date(today.year, 1, 1)
        end_date = today - timedelta(days=1)

        async with self.__db_session_manager.session() as session:
            profile = await self.__find_profile_reader.handle(session, user_id)
            if profile is None:
                raise AppException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    code="profile_not_found",
                    message=f"Profile for user '{user_id}' not found",
                )
            start_date = max(
                start_date, profile.work_start_date, MISS_CHECK_IN_COUNTING_START
            )
            if start_date > end_date:
                return []

            days = [
                start_date + timedelta(days=offset)
                for offset in range((end_date - start_date).days + 1)
            ]
            entries = await self.__find_attendance_entries_reader.handle(
                session, user_id, start_date, end_date
            )
            exceptions = await self.__find_workday_exceptions_reader.handle(
                session, days
            )

        missed_days = self.__find_missing_check_in_days_service.handle(
            start_date, end_date, entries, exceptions
        )
        return [day for day, _ in missed_days]


ListMissingCheckInDaysServiceDep = Annotated[ListMissingCheckInDaysService, Depends()]
