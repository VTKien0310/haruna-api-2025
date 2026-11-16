from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator


class UpdateAttendanceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def reject_null_fields(self) -> Self:
        for field in self.model_fields_set - {"note"}:
            if getattr(self, field) is None:
                raise ValueError(f"{field} must not be null")
        return self
