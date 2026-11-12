from datetime import date, time
from uuid import UUID, uuid4

import pytest
from sqlmodel import select

from app.core import AppException
from app.database import (
    DbSessionManager,
    LeaveWorkEntryRecord,
    PtoAffectEntryRecord,
    PtoBankRecord,
    PtoTransactionRecord,
)
from app.features.attendance.data import (
    CreateLeaveWorkEntryWriter,
    FindLeaveWorkEntriesByIdsAndDateReader,
)
from app.features.attendance.services import CreateLeaveWorkService
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

DAY = date(2026, 1, 5)
OTHER_USER_ID = str(uuid4())


def _service(db_session_manager: DbSessionManager) -> CreateLeaveWorkService:
    return CreateLeaveWorkService(
        FindPtoAffectEntriesByOwnerAndTypeReader(),
        FindLeaveWorkEntriesByIdsAndDateReader(),
        CreateLeaveWorkEntryWriter(),
        CreatePtoAffectEntryWriter(),
        NoopDeductPtoForEntryService(),
        db_session_manager,
    )


class _FailingAffectWriter:
    async def handle(self, *args: object, **kwargs: object) -> object:
        raise RuntimeError("force rollback")


async def test_stores_leave_work_and_its_affect_row(
    db_session_manager: DbSessionManager,
) -> None:
    leave_work = await _service(db_session_manager).handle(
        TEST_USER_ID, DAY, time(9, 0), time(10, 0)
    )

    assert leave_work.date == DAY
    assert leave_work.start == time(9, 0)
    assert leave_work.end == time(10, 0)

    async with db_session_manager.session() as session:
        record = await session.get(LeaveWorkEntryRecord, UUID(leave_work.id))
        affect_rows = (await session.exec(select(PtoAffectEntryRecord))).all()

    assert record is not None
    assert record.date == DAY
    assert record.start == time(9, 0)
    assert record.end == time(10, 0)
    assert len(affect_rows) == 1
    assert str(affect_rows[0].owner_id) == TEST_USER_ID
    assert str(affect_rows[0].entry_id) == leave_work.id
    assert affect_rows[0].entry_type == PtoAffectEntryType.LEAVE_WORK.value
    assert affect_rows[0].no_deduction == 0
    assert affect_rows[0].note == ""


async def test_stores_an_optional_affect_note(
    db_session_manager: DbSessionManager,
) -> None:
    await _service(db_session_manager).handle(
        TEST_USER_ID, DAY, time(9, 0), time(10, 0), note="clinic visit"
    )

    async with db_session_manager.session() as session:
        affect_rows = (await session.exec(select(PtoAffectEntryRecord))).all()

    assert len(affect_rows) == 1
    assert affect_rows[0].note == "clinic visit"


async def test_touching_leave_work_intervals_are_allowed(
    db_session_manager: DbSessionManager,
) -> None:
    service = _service(db_session_manager)
    await service.handle(TEST_USER_ID, DAY, time(10, 0), time(11, 0))

    after = await service.handle(TEST_USER_ID, DAY, time(11, 0), time(12, 0))
    before = await service.handle(TEST_USER_ID, DAY, time(9, 0), time(10, 0))

    assert after.start == time(11, 0)
    assert before.end == time(10, 0)


async def test_overlapping_leave_work_is_rejected(
    db_session_manager: DbSessionManager,
) -> None:
    service = _service(db_session_manager)
    await service.handle(TEST_USER_ID, DAY, time(10, 0), time(11, 0))

    with pytest.raises(AppException) as exc_info:
        await service.handle(TEST_USER_ID, DAY, time(10, 30), time(11, 30))

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "leave_work_overlaps"
    assert str(DAY) in exc_info.value.detail


async def test_another_owner_leave_work_does_not_conflict(
    db_session_manager: DbSessionManager,
) -> None:
    service = _service(db_session_manager)
    await service.handle(OTHER_USER_ID, DAY, time(10, 0), time(11, 0))

    leave_work = await service.handle(TEST_USER_ID, DAY, time(10, 30), time(11, 30))

    assert leave_work.start == time(10, 30)


async def test_affect_insert_failure_rolls_back_leave_work_entry(
    db_session_manager: DbSessionManager,
) -> None:
    service = CreateLeaveWorkService(
        FindPtoAffectEntriesByOwnerAndTypeReader(),
        FindLeaveWorkEntriesByIdsAndDateReader(),
        CreateLeaveWorkEntryWriter(),
        _FailingAffectWriter(),
        make_deduct_pto_for_entry_service(db_session_manager),
        db_session_manager,
    )

    with pytest.raises(RuntimeError, match="force rollback"):
        await service.handle(TEST_USER_ID, DAY, time(9, 0), time(10, 0))

    async with db_session_manager.session() as session:
        records = (await session.exec(select(LeaveWorkEntryRecord))).all()
        affect_rows = (await session.exec(select(PtoAffectEntryRecord))).all()

    assert records == []
    assert affect_rows == []


async def test_leave_work_creates_a_pto_transaction_for_the_interval(
    db_session_manager: DbSessionManager,
) -> None:
    async with db_session_manager.transaction() as session:
        session.add(make_profile_record())
        session.add(
            make_pto_bank_record(year=2026, annual_balance=600, seniority_balance=0)
        )

    service = CreateLeaveWorkService(
        FindPtoAffectEntriesByOwnerAndTypeReader(),
        FindLeaveWorkEntriesByIdsAndDateReader(),
        CreateLeaveWorkEntryWriter(),
        CreatePtoAffectEntryWriter(),
        make_deduct_pto_for_entry_service(db_session_manager),
        db_session_manager,
    )
    leave_work = await service.handle(TEST_USER_ID, DAY, time(9, 0), time(10, 30))
    assert leave_work.end == time(10, 30)

    async with db_session_manager.session() as session:
        transactions = (await session.exec(select(PtoTransactionRecord))).all()
        affect_rows = (await session.exec(select(PtoAffectEntryRecord))).all()
        banks = (await session.exec(select(PtoBankRecord))).all()

    assert len(transactions) == 1
    transaction = transactions[0]
    assert transaction.cause == "leave_work_entries_create"
    assert transaction.value == 90
    assert transaction.exceed_bank_value == 0
    assert str(transaction.entry_id) == str(affect_rows[0].id)
    assert str(transaction.pto_bank_id) == str(banks[0].id)
    assert banks[0].annual_balance == 510


async def test_leave_work_with_no_deduction_creates_no_pto_transaction(
    db_session_manager: DbSessionManager,
) -> None:
    await _service(db_session_manager).handle(
        TEST_USER_ID, DAY, time(9, 0), time(10, 0), no_deduction=1
    )

    async with db_session_manager.session() as session:
        transactions = (await session.exec(select(PtoTransactionRecord))).all()

    assert transactions == []
