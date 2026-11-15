from datetime import time
from typing import Annotated

from fastapi import Depends

from app.features.attendance.constants import WORK_START_MINUTES


class CalculateCheckInPenaltyService:
    def handle(self, arrival: time) -> int:
        return max(arrival.hour * 60 + arrival.minute - WORK_START_MINUTES, 0)


CalculateCheckInPenaltyServiceDep = Annotated[CalculateCheckInPenaltyService, Depends()]
