from datetime import date as datetime_date

from pydantic import Field
from pydantic.json_schema import SkipJsonSchema

from app.features.attendance.entities import RemoteWorkType
from app.features.attendance.requests import UpdateAttendanceRequest


class UpdateRemoteWorkRequest(UpdateAttendanceRequest):
    date: datetime_date | SkipJsonSchema[None] = Field(
        default=None, description="Replacement date within the original year."
    )
    type: RemoteWorkType | SkipJsonSchema[None] = Field(
        default=None, description="Replacement type; omitted values stay unchanged."
    )
    title: str | SkipJsonSchema[None] = Field(
        default=None,
        description="Replacement PTO affect title; omit to preserve it. Null is rejected.",
    )
    note: str | None = Field(
        default=None, description="Omit to preserve the note; null clears it."
    )
