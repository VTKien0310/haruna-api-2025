from datetime import date as datetime_date
from datetime import time

from pydantic import Field
from pydantic.json_schema import SkipJsonSchema

from app.features.attendance.requests import UpdateAttendanceRequest


class UpdateLeaveWorkRequest(UpdateAttendanceRequest):
    date: datetime_date | SkipJsonSchema[None] = Field(
        default=None, description="Replacement date within the original year."
    )
    start: time | SkipJsonSchema[None] = Field(
        default=None, description="Replacement start; omitted values stay unchanged."
    )
    end: time | SkipJsonSchema[None] = Field(
        default=None, description="Replacement end; omitted values stay unchanged."
    )
    no_deduction: int | SkipJsonSchema[None] = Field(
        default=None, ge=0, le=1, description="0 applies deduction; 1 skips it."
    )
    title: str | SkipJsonSchema[None] = Field(
        default=None,
        description="Replacement PTO affect title; omit to preserve it. Null is rejected.",
    )
    note: str | None = Field(
        default=None, description="Omit to preserve the note; null clears it."
    )
