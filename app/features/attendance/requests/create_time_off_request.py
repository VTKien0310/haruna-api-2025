from datetime import date
from typing import Self

from pydantic import BaseModel, Field, model_validator

from app.features.attendance.entities import TimeOffType


class CreateTimeOffRequest(BaseModel):
    start_date: date = Field(description="First calendar date of the time off.")
    end_date: date | None = Field(
        default=None,
        description="Last calendar date, inclusive; defaults to start_date.",
    )
    type: TimeOffType = Field(
        description="0 for full day, 1 for morning, or 2 for afternoon."
    )

    @model_validator(mode="after")
    def validate_date_range(self) -> Self:
        end_date = self.end_date or self.start_date
        if end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        if (end_date - self.start_date).days >= 366:
            raise ValueError("time-off range must not exceed 366 dates")
        if end_date > self.start_date and self.type != TimeOffType.FULL_DAY:
            raise ValueError("multi-date time off must be full day")
        return self
