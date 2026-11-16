from datetime import date as datetime_date
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from pydantic.json_schema import SkipJsonSchema

from app.features.attendance.entities import WorkdayExceptionTime, WorkdayExceptionType


class UpdateWorkdayExceptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: WorkdayExceptionType | SkipJsonSchema[None] = Field(
        default=None, description="Replacement exception type; omit to preserve."
    )
    date: datetime_date | SkipJsonSchema[None] = Field(
        default=None,
        description="Replacement date, today or later in Asia/Ho_Chi_Minh.",
    )
    time: WorkdayExceptionTime | SkipJsonSchema[None] = Field(
        default=None, description="Replacement period; omit to preserve."
    )
    title: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
        | SkipJsonSchema[None]
    ) = Field(default=None, description="Replacement nonblank title; omit to preserve.")

    @model_validator(mode="after")
    def validate_changes(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        if any(getattr(self, name) is None for name in self.model_fields_set):
            raise ValueError("Fields must not be null")
        return self
