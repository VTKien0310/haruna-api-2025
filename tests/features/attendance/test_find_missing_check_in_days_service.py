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

MONDAY = date(2026, 1, 5)
TUESDAY = date(2026, 1, 6)
WEDNESDAY = date(2026, 1, 7)
THURSDAY = date(2026, 1, 8)
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


def _service() -> FindMissingCheckInDaysService:
    return FindMissingCheckInDaysService(
        GetWorkingShiftsService(), CalculateMissCheckInPenaltyService()
    )


def test_returns_only_positive_penalties_in_chronological_order() -> None:
    entries = [
        (
            _affect("check-in", PtoAffectEntryType.CHECK_IN),
            CheckInEntry(id="check-in", date=MONDAY, time=time(9)),
        ),
        (
            _affect("remote-work", PtoAffectEntryType.REMOTE_WORK),
            RemoteWorkEntry(
                id="remote-work", date=TUESDAY, type=RemoteWorkType.FULL_DAY
            ),
        ),
        (
            _affect("leave-work", PtoAffectEntryType.LEAVE_WORK),
            LeaveWorkEntry(
                id="leave-work",
                date=WEDNESDAY,
                start=time(9),
                end=time(10),
            ),
        ),
    ]

    missing_days = _service().handle(MONDAY, THURSDAY, entries, [])

    assert missing_days == [(WEDNESDAY, 420), (THURSDAY, 480)]


def test_empty_or_reversed_range_returns_no_days() -> None:
    service = _service()

    assert service.handle(MONDAY, MONDAY, [], []) == [(MONDAY, 480)]
    assert service.handle(TUESDAY, MONDAY, [], []) == []
