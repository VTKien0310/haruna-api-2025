from datetime import date, datetime, time, timezone

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
from app.features.attendance.services import CalculateMissCheckInPenaltyService
from app.features.pto.entities import PtoAffectEntry, PtoAffectEntryType

DAY = date(2026, 1, 5)
NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _affect(entry_id: str, entry_type: PtoAffectEntryType) -> PtoAffectEntry:
    return PtoAffectEntry(
        id=f"affect-{entry_id}",
        owner_id="owner",
        entry_id=entry_id,
        entry_type=entry_type,
        no_deduction=False,
        note="",
        title="",
        created_at=NOW,
        updated_at=NOW,
    )


def test_counts_overlapping_attendance_coverage_only_once() -> None:
    entries = [
        (
            _affect("work-time", PtoAffectEntryType.WORK_TIME),
            WorkTimeEntry(
                id="work-time",
                date=DAY,
                type=WorkTimeType.LATE_FOR_WORK,
                duration=30,
                time=WorkTimeShift.MORNING,
            ),
        ),
        (
            _affect("leave-work", PtoAffectEntryType.LEAVE_WORK),
            LeaveWorkEntry(
                id="leave-work",
                date=DAY,
                start=time(8, 15),
                end=time(8, 45),
            ),
        ),
        (
            _affect("remote-work", PtoAffectEntryType.REMOTE_WORK),
            RemoteWorkEntry(id="remote-work", date=DAY, type=RemoteWorkType.AFTERNOON),
        ),
    ]

    penalty = CalculateMissCheckInPenaltyService().handle(
        {WorkdayExceptionTime.MORNING, WorkdayExceptionTime.AFTERNOON}, entries
    )

    assert penalty == 195


def test_paid_time_off_and_remote_work_cover_the_entire_scheduled_day() -> None:
    entries = [
        (
            _affect("time-off", PtoAffectEntryType.TIME_OFF),
            TimeOffEntry(id="time-off", date=DAY, type=TimeOffType.MORNING),
        ),
        (
            _affect("leave-work", PtoAffectEntryType.LEAVE_WORK),
            LeaveWorkEntry(
                id="leave-work",
                date=DAY,
                start=time(10),
                end=time(11),
            ),
        ),
        (
            _affect("remote-work", PtoAffectEntryType.REMOTE_WORK),
            RemoteWorkEntry(id="remote-work", date=DAY, type=RemoteWorkType.AFTERNOON),
        ),
    ]

    penalty = CalculateMissCheckInPenaltyService().handle(
        {WorkdayExceptionTime.MORNING, WorkdayExceptionTime.AFTERNOON}, entries
    )

    assert penalty == 0


def test_clips_coverage_to_the_scheduled_shift() -> None:
    entries = [
        (
            _affect("leave-work", PtoAffectEntryType.LEAVE_WORK),
            LeaveWorkEntry(
                id="leave-work",
                date=DAY,
                start=time(7, 30),
                end=time(8, 30),
            ),
        )
    ]

    penalty = CalculateMissCheckInPenaltyService().handle(
        {WorkdayExceptionTime.MORNING}, entries
    )

    assert penalty == 210


def test_returns_only_partially_uncovered_shift_minutes() -> None:
    entries = [
        (
            _affect("leave-work", PtoAffectEntryType.LEAVE_WORK),
            LeaveWorkEntry(
                id="leave-work",
                date=DAY,
                start=time(9),
                end=time(10),
            ),
        )
    ]

    penalty = CalculateMissCheckInPenaltyService().handle(
        {WorkdayExceptionTime.MORNING}, entries
    )

    assert penalty == 180
