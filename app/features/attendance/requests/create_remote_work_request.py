from datetime import date as datetime_date

from pydantic import BaseModel, Field

from app.features.attendance.entities import RemoteWorkType


class CreateRemoteWorkRequest(BaseModel):
    date: datetime_date = Field(description="Calendar date of the remote work.")
    type: RemoteWorkType = Field(
        description="0 for full day, 1 for morning, or 2 for afternoon."
    )
    title: str = Field(
        default="Untitled",
        description="Title stored on each linked PTO affect entry; defaults to Untitled.",
    )
    note: str | None = Field(
        default=None,
        description=(
            "Optional note stored on the linked PTO affect entry. "
            "An omitted or null note is stored as an empty string."
        ),
    )
