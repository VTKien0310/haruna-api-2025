from datetime import date as datetime_date

from pydantic import Field
from pydantic.json_schema import SkipJsonSchema

from app.features.attendance.entities import WorkTimeShift, WorkTimeType
from app.features.attendance.requests import UpdateAttendanceRequest


class UpdateWorkTimeRequest(UpdateAttendanceRequest):
    date: datetime_date | SkipJsonSchema[None] = Field(
        default=None, description="Replacement date within the original year."
    )
    time: WorkTimeShift | SkipJsonSchema[None] = Field(
        default=None, description="Replacement time; omitted values stay unchanged."
    )
    type: WorkTimeType | SkipJsonSchema[None] = Field(
        default=None, description="Replacement type; omitted values stay unchanged."
    )
    duration: int | SkipJsonSchema[None] = Field(
        default=None,
        ge=1,
        le=240,
        description="Replacement duration; omitted values stay unchanged.",
    )
    no_deduction: int | SkipJsonSchema[None] = Field(
        default=None, ge=0, le=1, description="0 applies deduction; 1 skips it."
    )
    note: str | None = Field(
        default=None, description="Omit to preserve the note; null clears it."
    )
