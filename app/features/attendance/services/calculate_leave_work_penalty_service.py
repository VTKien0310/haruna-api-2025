from datetime import time
from typing import Annotated

from fastapi import Depends


class CalculateLeaveWorkPenaltyService:
    def handle(self, start: time, end: time) -> int:
        return max(end.hour * 60 + end.minute - start.hour * 60 - start.minute, 0)


CalculateLeaveWorkPenaltyServiceDep = Annotated[
    CalculateLeaveWorkPenaltyService, Depends()
]
