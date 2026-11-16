from datetime import date, datetime, timezone, tzinfo

import pytest

from app.features.attendance.services import GetWorkdayExceptionTodayService


def test_vietnam_today(monkeypatch: pytest.MonkeyPatch) -> None:
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz: tzinfo | None = None) -> datetime:
            return datetime(2026, 11, 15, 18, 0, tzinfo=timezone.utc).astimezone(tz)

    monkeypatch.setattr(
        "app.features.attendance.services.get_workday_exception_today_service.datetime",
        FrozenDatetime,
    )
    assert GetWorkdayExceptionTodayService().handle() == date(2026, 11, 16)
