from datetime import date, datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends


class GetWorkdayExceptionTodayService:
    def handle(self) -> date:
        return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()


GetWorkdayExceptionTodayServiceDep = Annotated[
    GetWorkdayExceptionTodayService, Depends()
]
