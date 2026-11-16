from datetime import date as datetime_date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.features.attendance.entities import WorkdayExceptionTime, WorkdayExceptionType


class CreateWorkdayExceptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: WorkdayExceptionType = Field(description="Workday (0) or holiday (1).")
    date: datetime_date = Field(
        description="Exception date, today or later in Asia/Ho_Chi_Minh."
    )
    time: WorkdayExceptionTime = Field(
        description="Full day (0), morning (1), or afternoon (2)."
    )
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] = (
        Field(description="Nonblank exception title.")
    )
