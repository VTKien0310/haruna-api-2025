from datetime import date, datetime, time, timezone

from app.features.attendance.entities import (
    CheckInEntry,
    LeaveWorkEntry,
    RemoteWorkEntry,
    RemoteWorkType,
)
from app.features.attendance.services import (
    CalculateMissCheckInPenaltyService,
    FindMissingCheckInDaysService,
    GetWorkingShiftsService,
)
from app.features.pto.entities import PtoAffectEntry, PtoAffectEntryType

BEFORE_GO_LIVE_MONDAY = date(2026, 11, 16)
BEFORE_GO_LIVE_TUESDAY = date(2026, 11, 17)
GO_LIVE_WEDNESDAY = date(2026, 11, 18)
THURSDAY = date(2026, 11, 19)
FRIDAY = date(2026, 11, 20)
MONDAY = date(2026, 11, 23)
NOW = datetime(2026, 11, 18, tzinfo=timezone.utc)


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


def _service() -> FindMissingCheckInDaysService:
    return FindMissingCheckInDaysService(
        GetWorkingShiftsService(), CalculateMissCheckInPenaltyService()
    )


def test_returns_only_positive_penalties_in_chronological_order() -> None:
    entries = [
        (
            _affect("check-in", PtoAffectEntryType.CHECK_IN),
            CheckInEntry(id="check-in", date=GO_LIVE_WEDNESDAY, time=time(9)),
        ),
        (
            _affect("remote-work", PtoAffectEntryType.REMOTE_WORK),
            RemoteWorkEntry(
                id="remote-work", date=THURSDAY, type=RemoteWorkType.FULL_DAY
            ),
        ),
        (
            _affect("leave-work", PtoAffectEntryType.LEAVE_WORK),
            LeaveWorkEntry(
                id="leave-work",
                date=FRIDAY,
                start=time(9),
                end=time(10),
            ),
        ),
    ]

    missing_days = _service().handle(GO_LIVE_WEDNESDAY, MONDAY, entries, [])

    assert missing_days == [(FRIDAY, 420), (MONDAY, 480)]


def test_empty_or_reversed_range_returns_no_days() -> None:
    service = _service()

    assert service.handle(GO_LIVE_WEDNESDAY, GO_LIVE_WEDNESDAY, [], []) == [
        (GO_LIVE_WEDNESDAY, 480)
    ]
    assert service.handle(THURSDAY, GO_LIVE_WEDNESDAY, [], []) == []


def test_omits_weekdays_before_go_live() -> None:
    missing_days = _service().handle(BEFORE_GO_LIVE_MONDAY, GO_LIVE_WEDNESDAY, [], [])

    assert missing_days == [(GO_LIVE_WEDNESDAY, 480)]
    assert BEFORE_GO_LIVE_TUESDAY not in {day for day, _ in missing_days}
