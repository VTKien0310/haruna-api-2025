from datetime import date, datetime, timezone

from app.features.attendance.entities import (
    WorkdayException,
    WorkdayExceptionTime,
    WorkdayExceptionType,
)
from app.features.attendance.services import GetWorkingShiftsService

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _exception(
    day: date,
    exception_type: WorkdayExceptionType,
    exception_time: WorkdayExceptionTime,
) -> WorkdayException:
    return WorkdayException(
        id="exception",
        type=exception_type,
        date=day,
        time=exception_time,
        title="",
        created_at=NOW,
        updated_at=NOW,
    )


def test_weekdays_are_scheduled_and_weekends_are_not() -> None:
    service = GetWorkingShiftsService()

    assert service.handle(date(2026, 1, 5), []) == {
        WorkdayExceptionTime.MORNING,
        WorkdayExceptionTime.AFTERNOON,
    }
    assert service.handle(date(2026, 1, 10), []) == set()


def test_workday_exception_schedules_only_its_weekend_shift() -> None:
    day = date(2026, 1, 10)
    exception = _exception(
        day, WorkdayExceptionType.WORKDAY, WorkdayExceptionTime.MORNING
    )

    assert GetWorkingShiftsService().handle(day, [exception]) == {
        WorkdayExceptionTime.MORNING
    }


def test_holiday_exception_overrides_only_its_weekday_shift() -> None:
    day = date(2026, 1, 5)
    exception = _exception(
        day, WorkdayExceptionType.HOLIDAY, WorkdayExceptionTime.MORNING
    )

    assert GetWorkingShiftsService().handle(day, [exception]) == {
        WorkdayExceptionTime.AFTERNOON
    }
