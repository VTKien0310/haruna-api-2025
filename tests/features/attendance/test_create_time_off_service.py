from datetime import date
from uuid import uuid4

import pytest
from sqlmodel import select

from app.core import AppException
from app.database import (
    DbSessionManager,
    PtoAffectEntryRecord,
    PtoBankRecord,
    PtoTransactionRecord,
    TimeOffEntryRecord,
)
from app.features.attendance.data import (
    CreateTimeOffEntryWriter,
    FindTimeOffEntriesByIdsAndDatesReader,
)
from app.features.attendance.entities import TimeOffType
from app.features.attendance.services import CreateTimeOffService
from app.features.pto.data import (
    CreatePtoAffectEntryWriter,
    FindPtoAffectEntriesByOwnerAndTypeReader,
)
from app.features.pto.entities import PtoAffectEntryType
from tests.factories.database_records import (
    TEST_USER_ID,
    make_pto_bank_record,
    make_profile_record,
)
from tests.support.pto_services import (
    NoopDeductPtoForEntryService,
    make_deduct_pto_for_entry_service,
)

FIRST_DAY = date(2026, 1, 5)
OTHER_USER_ID = str(uuid4())


def _service(db_session_manager: DbSessionManager) -> CreateTimeOffService:
    return CreateTimeOffService(
        FindPtoAffectEntriesByOwnerAndTypeReader(),
        FindTimeOffEntriesByIdsAndDatesReader(),
        CreateTimeOffEntryWriter(),
        CreatePtoAffectEntryWriter(),
        NoopDeductPtoForEntryService(),
        db_session_manager,
    )


class _FailingAffectWriter:
    async def handle(self, *args: object, **kwargs: object) -> object:
        raise RuntimeError("force rollback")


async def test_creates_one_entry_and_affect_row_for_each_date(
    db_session_manager: DbSessionManager,
) -> None:
    entries = await _service(db_session_manager).handle(
        TEST_USER_ID, FIRST_DAY, date(2026, 1, 7), TimeOffType.FULL_DAY
    )

    assert [entry.date for entry in entries] == [
        date(2026, 1, 5),
        date(2026, 1, 6),
        date(2026, 1, 7),
    ]
    assert all(entry.type == TimeOffType.FULL_DAY for entry in entries)

    async with db_session_manager.session() as session:
        records = (await session.exec(select(TimeOffEntryRecord))).all()
        affect_rows = (await session.exec(select(PtoAffectEntryRecord))).all()

    assert len(records) == len(affect_rows) == 3
    assert {str(row.id) for row in records} == {entry.id for entry in entries}
    assert {str(row.entry_id) for row in affect_rows} == {entry.id for entry in entries}
    assert {str(row.owner_id) for row in affect_rows} == {TEST_USER_ID}
    assert {row.entry_type for row in affect_rows} == {
        PtoAffectEntryType.TIME_OFF.value
    }
    assert {row.no_deduction for row in affect_rows} == {0}
    assert {row.note for row in affect_rows} == {""}


async def test_stores_the_same_optional_note_on_every_affect_row(
    db_session_manager: DbSessionManager,
) -> None:
    await _service(db_session_manager).handle(
        TEST_USER_ID,
        FIRST_DAY,
        date(2026, 1, 6),
        TimeOffType.FULL_DAY,
        note="family trip",
    )

    async with db_session_manager.session() as session:
        affect_rows = (await session.exec(select(PtoAffectEntryRecord))).all()

    assert len(affect_rows) == 2
    assert {row.note for row in affect_rows} == {"family trip"}


async def test_morning_and_afternoon_time_off_can_coexist(
    db_session_manager: DbSessionManager,
) -> None:
    service = _service(db_session_manager)

    morning = await service.handle(TEST_USER_ID, FIRST_DAY, None, TimeOffType.MORNING)
    afternoon = await service.handle(
        TEST_USER_ID, FIRST_DAY, None, TimeOffType.AFTERNOON
    )

    assert morning[0].type == TimeOffType.MORNING
    assert afternoon[0].type == TimeOffType.AFTERNOON


@pytest.mark.parametrize(
    ("existing_type", "new_type"),
    [
        (TimeOffType.FULL_DAY, TimeOffType.MORNING),
        (TimeOffType.MORNING, TimeOffType.FULL_DAY),
        (TimeOffType.AFTERNOON, TimeOffType.AFTERNOON),
    ],
)
async def test_conflicting_time_off_is_rejected(
    db_session_manager: DbSessionManager,
    existing_type: TimeOffType,
    new_type: TimeOffType,
) -> None:
    service = _service(db_session_manager)
    await service.handle(TEST_USER_ID, FIRST_DAY, None, existing_type)

    with pytest.raises(AppException) as exc_info:
        await service.handle(TEST_USER_ID, FIRST_DAY, None, new_type)

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "time_off_already_exists"
    assert str(FIRST_DAY) in exc_info.value.detail


async def test_conflict_in_date_range_prevents_all_range_inserts(
    db_session_manager: DbSessionManager,
) -> None:
    service = _service(db_session_manager)
    conflict_day = date(2026, 1, 6)
    await service.handle(TEST_USER_ID, conflict_day, None, TimeOffType.MORNING)

    with pytest.raises(AppException) as exc_info:
        await service.handle(
            TEST_USER_ID, FIRST_DAY, date(2026, 1, 7), TimeOffType.FULL_DAY
        )

    assert exc_info.value.code == "time_off_already_exists"
    assert str(conflict_day) in exc_info.value.detail

    async with db_session_manager.session() as session:
        records = (await session.exec(select(TimeOffEntryRecord))).all()
        affect_rows = (await session.exec(select(PtoAffectEntryRecord))).all()

    assert len(records) == len(affect_rows) == 1
    assert records[0].date == conflict_day


async def test_another_owner_time_off_does_not_conflict(
    db_session_manager: DbSessionManager,
) -> None:
    service = _service(db_session_manager)
    await service.handle(OTHER_USER_ID, FIRST_DAY, None, TimeOffType.FULL_DAY)

    entry = await service.handle(TEST_USER_ID, FIRST_DAY, None, TimeOffType.MORNING)

    assert entry[0].type == TimeOffType.MORNING
    async with db_session_manager.session() as session:
        affect_rows = (await session.exec(select(PtoAffectEntryRecord))).all()

    assert {str(row.owner_id) for row in affect_rows} == {TEST_USER_ID, OTHER_USER_ID}


async def test_affect_insert_failure_rolls_back_time_off_entry(
    db_session_manager: DbSessionManager,
) -> None:
    service = CreateTimeOffService(
        FindPtoAffectEntriesByOwnerAndTypeReader(),
        FindTimeOffEntriesByIdsAndDatesReader(),
        CreateTimeOffEntryWriter(),
        _FailingAffectWriter(),
        make_deduct_pto_for_entry_service(db_session_manager),
        db_session_manager,
    )

    with pytest.raises(RuntimeError, match="force rollback"):
        await service.handle(TEST_USER_ID, FIRST_DAY, None, TimeOffType.FULL_DAY)

    async with db_session_manager.session() as session:
        records = (await session.exec(select(TimeOffEntryRecord))).all()
        affect_rows = (await session.exec(select(PtoAffectEntryRecord))).all()

    assert records == []
    assert affect_rows == []


async def test_full_day_time_off_creates_a_pto_transaction_per_day(
    db_session_manager: DbSessionManager,
) -> None:
    async with db_session_manager.transaction() as session:
        session.add(make_profile_record())
        session.add(
            make_pto_bank_record(year=2026, annual_balance=1000, seniority_balance=0)
        )

    service = CreateTimeOffService(
        FindPtoAffectEntriesByOwnerAndTypeReader(),
        FindTimeOffEntriesByIdsAndDatesReader(),
        CreateTimeOffEntryWriter(),
        CreatePtoAffectEntryWriter(),
        make_deduct_pto_for_entry_service(db_session_manager),
        db_session_manager,
    )
    entries = await service.handle(
        TEST_USER_ID, FIRST_DAY, date(2026, 1, 6), TimeOffType.FULL_DAY
    )
    assert len(entries) == 2

    async with db_session_manager.session() as session:
        transactions = (await session.exec(select(PtoTransactionRecord))).all()
        banks = (await session.exec(select(PtoBankRecord))).all()

    assert len(transactions) == 2
    assert {transaction.cause for transaction in transactions} == {
        "time_off_entries_create"
    }
    assert {transaction.value for transaction in transactions} == {480}
    assert {transaction.exceed_bank_value for transaction in transactions} == {0}
    assert banks[0].annual_balance == 40


async def test_half_day_time_off_deducts_one_shift(
    db_session_manager: DbSessionManager,
) -> None:
    async with db_session_manager.transaction() as session:
        session.add(make_profile_record())
        session.add(
            make_pto_bank_record(year=2026, annual_balance=600, seniority_balance=0)
        )

    service = CreateTimeOffService(
        FindPtoAffectEntriesByOwnerAndTypeReader(),
        FindTimeOffEntriesByIdsAndDatesReader(),
        CreateTimeOffEntryWriter(),
        CreatePtoAffectEntryWriter(),
        make_deduct_pto_for_entry_service(db_session_manager),
        db_session_manager,
    )
    await service.handle(TEST_USER_ID, FIRST_DAY, None, TimeOffType.MORNING)

    async with db_session_manager.session() as session:
        transactions = (await session.exec(select(PtoTransactionRecord))).all()
        banks = (await session.exec(select(PtoBankRecord))).all()

    assert len(transactions) == 1
    assert transactions[0].value == 240
    assert banks[0].annual_balance == 360


async def test_time_off_with_no_deduction_creates_no_pto_transaction(
    db_session_manager: DbSessionManager,
) -> None:
    await _service(db_session_manager).handle(
        TEST_USER_ID, FIRST_DAY, None, TimeOffType.FULL_DAY, no_deduction=1
    )

    async with db_session_manager.session() as session:
        transactions = (await session.exec(select(PtoTransactionRecord))).all()

    assert transactions == []
