from typing import Annotated

from fastapi import Depends

from app.features.attendance.entities import TimeOffType
from app.features.pto.constants import MINUTES_PER_WORK_DAY, SHIFT_MINUTES


class CalculateTimeOffPenaltyService:
    def handle(self, entry_type: TimeOffType) -> int:
        return (
            MINUTES_PER_WORK_DAY
            if entry_type == TimeOffType.FULL_DAY
            else SHIFT_MINUTES
        )


CalculateTimeOffPenaltyServiceDep = Annotated[CalculateTimeOffPenaltyService, Depends()]
