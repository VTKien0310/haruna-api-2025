from datetime import date as datetime_date
from datetime import time
from typing import Self

from pydantic import BaseModel, Field, model_validator


class CreateLeaveWorkRequest(BaseModel):
    date: datetime_date = Field(description="Calendar date of the temporary absence.")
    start: time = Field(description="Local start time; seconds are ignored.")
    end: time = Field(description="Local end time; seconds are ignored.")
    no_deduction: int | None = Field(
        default=None,
        ge=0,
        le=1,
        description=(
            "PTO deduction flag: 0 applies normal deduction and 1 skips deduction. "
            "Defaults to 0 when omitted."
        ),
    )

    @model_validator(mode="after")
    def normalize_and_validate_interval(self) -> Self:
        self.start = self.start.replace(second=0, microsecond=0)
        self.end = self.end.replace(second=0, microsecond=0)
        if self.start >= self.end:
            raise ValueError("start must be before end after dropping seconds")
        return self
