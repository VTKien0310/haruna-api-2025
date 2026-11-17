from datetime import date, time

import pytest

from app.core import AppException
from app.database import DbSessionManager, WorkdayExceptionRecord
from app.features.attendance.data import FindWorkdayExceptionsByDatesReader
from app.features.attendance.entities import WorkdayExceptionTime
from app.features.attendance.services import (
    GetWorkingShiftsService,
    ValidateAttendanceWorkdayService,
)


@pytest.mark.parametrize(
    "weekend,exceptions,period,interval,allowed",
    [
        (True, [(0, 1)], 1, None, True),
        (True, [(0, 1)], 2, None, False),
        (True, [(0, 1)], 0, None, False),
        (True, [(0, 1), (0, 2)], 0, None, True),
        (True, [(0, 0), (1, 1)], 1, None, False),
        (True, [(1, 1), (0, 0)], 1, None, False),
        (True, [(0, 0), (1, 1)], 2, None, True),
        (False, [(1, 1)], 1, None, False),
        (False, [(1, 1)], 2, None, True),
        (False, [(1, 2)], 0, None, False),
        (False, [(1, 1)], 0, (time(13, 30), time(14)), True),
        (False, [(1, 2)], 0, (time(11), time(12)), True),
        (False, [(1, 2)], 0, (time(11), time(14)), False),
        (False, [(1, 1)], 0, (time(9), time(10)), False),
        (True, [], 0, (time(12), time(13, 30)), False),
        (True, [(0, 2)], 0, (time(12), time(13, 30)), True),
        (False, [(1, 0)], 0, (time(18), time(19)), False),
        (False, [], 0, (time(18), time(19)), True),
    ],
)
async def test_shift_coverage(
    db_session_manager: DbSessionManager,
    weekend: bool,
    exceptions: list[tuple[int, int]],
    period: int,
    interval: tuple[time, time] | None,
    allowed: bool,
) -> None:
    day = date(2026, 1, 10 if weekend else 5)
    async with db_session_manager.transaction() as session:
        for kind, shift in exceptions:
            session.add(
                WorkdayExceptionRecord(
                    date=day, type=kind, time=shift, title="Exception"
                )
            )
        # Unrelated dates must not affect validation.
        session.add(
            WorkdayExceptionRecord(
                date=date(2026, 1, 20), type=1, time=0, title="Other date"
            )
        )
    service = ValidateAttendanceWorkdayService(
        FindWorkdayExceptionsByDatesReader(), GetWorkingShiftsService()
    )
    async with db_session_manager.session() as session:
        if allowed:
            await service.handle(
                session, [day], WorkdayExceptionTime(period), interval=interval
            )
        else:
            with pytest.raises(AppException) as error:
                await service.handle(
                    session, [day], WorkdayExceptionTime(period), interval=interval
                )
            assert error.value.status_code == 409
            assert error.value.code == "attendance_non_workday"
