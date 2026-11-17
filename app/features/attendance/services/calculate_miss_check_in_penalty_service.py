from typing import Annotated

from fastapi import Depends

from app.features.attendance.entities import (
    LeaveWorkEntry,
    RemoteWorkEntry,
    RemoteWorkType,
    TimeOffEntry,
    TimeOffType,
    WorkTimeEntry,
    WorkTimeShift,
    WorkTimeType,
    WorkdayExceptionTime,
)
from app.features.attendance.types import AttendanceEntry, AttendanceEntryWithAffect

_MinuteInterval = tuple[int, int]
_SHIFT_INTERVALS: dict[WorkdayExceptionTime, _MinuteInterval] = {
    WorkdayExceptionTime.MORNING: (8 * 60, 12 * 60),
    WorkdayExceptionTime.AFTERNOON: (13 * 60 + 30, 17 * 60 + 30),
}


class CalculateMissCheckInPenaltyService:
    def handle(
        self,
        scheduled_shifts: set[WorkdayExceptionTime],
        entries: list[AttendanceEntryWithAffect],
    ) -> int:
        intervals = [
            interval
            for _, entry in entries
            for interval in self.__coverage_intervals(entry)
        ]
        return sum(
            self.__uncovered_minutes(_SHIFT_INTERVALS[shift], intervals)
            for shift in scheduled_shifts
        )

    def __coverage_intervals(self, entry: AttendanceEntry) -> list[_MinuteInterval]:
        if isinstance(entry, RemoteWorkEntry):
            if entry.type == RemoteWorkType.FULL_DAY:
                return list(_SHIFT_INTERVALS.values())
            return [_SHIFT_INTERVALS[WorkdayExceptionTime(entry.type)]]
        if isinstance(entry, TimeOffEntry):
            if entry.type == TimeOffType.FULL_DAY:
                return list(_SHIFT_INTERVALS.values())
            return [_SHIFT_INTERVALS[WorkdayExceptionTime(entry.type)]]
        if isinstance(entry, LeaveWorkEntry):
            start = self.__minute_of_day(entry.start.hour, entry.start.minute)
            end = self.__minute_of_day(entry.end.hour, entry.end.minute)
            return [(start, end)] if start < end else []
        if isinstance(entry, WorkTimeEntry):
            shift = (
                WorkdayExceptionTime.MORNING
                if entry.time == WorkTimeShift.MORNING
                else WorkdayExceptionTime.AFTERNOON
            )
            start, end = _SHIFT_INTERVALS[shift]
            duration = min(max(entry.duration, 0), end - start)
            if entry.type == WorkTimeType.LATE_FOR_WORK:
                return [(start, start + duration)]
            return [(end - duration, end)]
        return []

    def __uncovered_minutes(
        self,
        scheduled_interval: _MinuteInterval,
        coverage_intervals: list[_MinuteInterval],
    ) -> int:
        start, end = scheduled_interval
        clipped = sorted(
            (max(start, coverage_start), min(end, coverage_end))
            for coverage_start, coverage_end in coverage_intervals
            if coverage_start < end and start < coverage_end
        )
        covered_minutes = 0
        covered_start: int | None = None
        covered_end: int | None = None
        for interval_start, interval_end in clipped:
            if covered_start is None:
                covered_start, covered_end = interval_start, interval_end
            elif interval_start <= covered_end:
                covered_end = max(covered_end, interval_end)
            else:
                covered_minutes += covered_end - covered_start
                covered_start, covered_end = interval_start, interval_end
        if covered_start is not None and covered_end is not None:
            covered_minutes += covered_end - covered_start
        return end - start - covered_minutes

    def __minute_of_day(self, hour: int, minute: int) -> int:
        return hour * 60 + minute


CalculateMissCheckInPenaltyServiceDep = Annotated[
    CalculateMissCheckInPenaltyService, Depends()
]
