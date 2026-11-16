from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.core import AppException


def workday_exception_today() -> date:
    return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()


def require_mutable_workday_exception(exception_date: date, today: date) -> None:
    if exception_date < today:
        raise AppException(
            status_code=409,
            code="past_workday_exception_immutable",
            message="Past workday exceptions cannot be changed",
        )
