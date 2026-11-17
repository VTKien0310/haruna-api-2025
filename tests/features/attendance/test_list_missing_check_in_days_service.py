from datetime import date, time
from uuid import UUID, uuid4

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

import app.features.attendance.services.list_missing_check_in_days_service as service_module
from app.core import AppException
from app.database import (
    CheckInEntryRecord,
    DbSessionManager,
    PtoAffectEntryRecord,
    RemoteWorkEntryRecord,
    TimeOffEntryRecord,
    WorkdayExceptionRecord,
)
from app.features.attendance.data import (
    FindOwnedPtoAttendanceEntriesByDateRangeReader,
    FindWorkdayExceptionsByDatesReader,
)
from app.features.attendance.entities import WorkdayExceptionTime
from app.features.attendance.services import (
    CalculateMissCheckInPenaltyService,
    FindMissingCheckInDaysService,
    GetWorkingShiftsService,
    ListMissingCheckInDaysService,
)
from app.features.profile.data import FindProfileByUserIdReader
from app.features.pto.entities import PtoAffectEntryType
from tests.factories.database_records import TEST_USER_ID, make_profile_record

OTHER_USER_ID = str(uuid4())
MONDAY = date(2026, 1, 5)
TUESDAY = date(2026, 1, 6)
WEDNESDAY = date(2026, 1, 7)
THURSDAY = date(2026, 1, 8)
FRIDAY = date(2026, 1, 9)
SATURDAY = date(2026, 1, 10)
SUNDAY = date(2026, 1, 11)


class _FixedDate(date):
    @classmethod
    def today(cls) -> date:
        return cls(2026, 1, 12)


def _service(db_session_manager: DbSessionManager) -> ListMissingCheckInDaysService:
    return ListMissingCheckInDaysService(
        FindProfileByUserIdReader(),
        FindOwnedPtoAttendanceEntriesByDateRangeReader(),
        FindWorkdayExceptionsByDatesReader(),
        db_session_manager,
        FindMissingCheckInDaysService(
            GetWorkingShiftsService(), CalculateMissCheckInPenaltyService()
        ),
    )


async def _add_owned_entry(
    session: AsyncSession,
    user_id: str,
    record: CheckInEntryRecord | RemoteWorkEntryRecord | TimeOffEntryRecord,
    entry_type: PtoAffectEntryType,
) -> None:
    session.add(record)
    session.add(
        PtoAffectEntryRecord(
            owner_id=UUID(user_id),
            entry_id=record.id,
            entry_type=entry_type.value,
        )
    )


@pytest.fixture(autouse=True)
def freeze_today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service_module, "date", _FixedDate)


async def test_lists_uncovered_days_with_schedule_coverage_and_owner_scope(
    db_session_manager: DbSessionManager,
) -> None:
    async with db_session_manager.transaction() as session:
        session.add(make_profile_record(work_start_date=MONDAY))
        await _add_owned_entry(
            session,
            OTHER_USER_ID,
            RemoteWorkEntryRecord(date=MONDAY, type=0),
            PtoAffectEntryType.REMOTE_WORK,
        )
        await _add_owned_entry(
            session,
            TEST_USER_ID,
            RemoteWorkEntryRecord(date=TUESDAY, type=0),
            PtoAffectEntryType.REMOTE_WORK,
        )
        await _add_owned_entry(
            session,
            TEST_USER_ID,
            TimeOffEntryRecord(date=WEDNESDAY, type=WorkdayExceptionTime.MORNING),
            PtoAffectEntryType.TIME_OFF,
        )
        await _add_owned_entry(
            session,
            TEST_USER_ID,
            CheckInEntryRecord(date=THURSDAY, time=time(9, 0)),
            PtoAffectEntryType.CHECK_IN,
        )
        session.add(
            WorkdayExceptionRecord(
                date=FRIDAY,
                type=1,
                time=WorkdayExceptionTime.FULL_DAY,
                title="Holiday",
            )
        )
        session.add(
            WorkdayExceptionRecord(
                date=SATURDAY,
                type=0,
                time=WorkdayExceptionTime.MORNING,
                title="Morning workday",
            )
        )
        session.add(
            WorkdayExceptionRecord(
                date=SUNDAY,
                type=0,
                time=WorkdayExceptionTime.AFTERNOON,
                title="Afternoon workday",
            )
        )

    missing_days = await _service(db_session_manager).handle(TEST_USER_ID)

    assert missing_days == [MONDAY, WEDNESDAY, SATURDAY, SUNDAY]


async def test_does_not_scan_before_employment_or_include_today(
    db_session_manager: DbSessionManager,
) -> None:
    async with db_session_manager.transaction() as session:
        session.add(make_profile_record(work_start_date=date(2026, 1, 12)))

    missing_days = await _service(db_session_manager).handle(TEST_USER_ID)

    assert missing_days == []


async def test_missing_days_requires_a_profile(
    db_session_manager: DbSessionManager,
) -> None:
    with pytest.raises(AppException) as error:
        await _service(db_session_manager).handle(TEST_USER_ID)

    assert error.value.status_code == 404
    assert error.value.code == "profile_not_found"
