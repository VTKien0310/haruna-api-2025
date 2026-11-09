from datetime import date as datetime_date

from pydantic import BaseModel, Field

from app.features.attendance.entities import WorkTimeShift, WorkTimeType


class CreateWorkTimeRequest(BaseModel):
    date: datetime_date = Field(description="Calendar date of the work-time entry.")
    time: WorkTimeShift = Field(description="Shift: 0 for morning or 1 for afternoon.")
    type: WorkTimeType = Field(
        description="0 for late coverage or 1 for leaving work early."
    )
    duration: int = Field(
        ge=1,
        le=240,
        description="Minutes of drift within the shift (1–240).",
    )
