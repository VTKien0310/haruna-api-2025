from datetime import date, time

from pydantic import BaseModel, Field


class CreateCheckInRequest(BaseModel):
    date: date
    time: time
    no_deduction: int | None = Field(
        default=None,
        ge=0,
        le=1,
        description=(
            "PTO deduction flag: 0 applies normal deduction and 1 skips deduction. "
            "Defaults to 0 when omitted."
        ),
    )
