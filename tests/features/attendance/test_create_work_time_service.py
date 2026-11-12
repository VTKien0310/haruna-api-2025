from datetime import date
from uuid import UUID, uuid4

import pytest
from sqlmodel import select

from app.core import AppException
from app.database import DbSessionManager, PtoAffectEntryRecord, WorkTimeEntryRecord
from app.features.attendance.data import (
    CreateWorkTimeEntryWriter,
    FindWorkTimeEntriesByIdsAndDateReader,
)
from app.features.attendance.entities import WorkTimeShift, WorkTimeType
from app.features.attendance.services import CreateWorkTimeService
from app.features.pto.data import (
    CreatePtoAffectEntryWriter,
    FindPtoAffectEntriesByOwnerAndTypeReader,
)
from app.features.pto.entities import PtoAffectEntryType
from tests.factories.database_records import TEST_USER_ID

DAY = date(2026, 1, 5)
OTHER_USER_ID = str(uuid4())


def _service(db_session_manager: DbSessionManager) -> CreateWorkTimeService:
    return CreateWorkTimeService(
        FindPtoAffectEntriesByOwnerAndTypeReader(),
        FindWorkTimeEntriesByIdsAndDateReader(),
        CreateWorkTimeEntryWriter(),
        CreatePtoAffectEntryWriter(),
        db_session_manager,
    )


class _FailingAffectWriter:
    async def handle(self, *args: object, **kwargs: object) -> object:
        raise RuntimeError("force rollback")


async def test_stores_work_time_and_its_affect_row(
    db_session_manager: DbSessionManager,
) -> None:
    work_time = await _service(db_session_manager).handle(
        TEST_USER_ID,
        DAY,
        WorkTimeShift.AFTERNOON,
        WorkTimeType.LATE_FOR_WORK,
        45,
    )

    assert work_time.date == DAY
    assert work_time.time == WorkTimeShift.AFTERNOON
    assert work_time.type == WorkTimeType.LATE_FOR_WORK
    assert work_time.duration == 45

    async with db_session_manager.session() as session:
        record = await session.get(WorkTimeEntryRecord, UUID(work_time.id))
        affect_rows = (await session.exec(select(PtoAffectEntryRecord))).all()

    assert record is not None
    assert record.date == DAY
    assert record.time == WorkTimeShift.AFTERNOON
    assert record.type == WorkTimeType.LATE_FOR_WORK
    assert record.duration == 45
    assert len(affect_rows) == 1
    assert str(affect_rows[0].owner_id) == TEST_USER_ID
    assert str(affect_rows[0].entry_id) == work_time.id
    assert affect_rows[0].entry_type == PtoAffectEntryType.WORK_TIME.value
    assert affect_rows[0].no_deduction == 0
    assert affect_rows[0].note == ""


async def test_stores_an_optional_affect_note(
    db_session_manager: DbSessionManager,
) -> None:
    await _service(db_session_manager).handle(
        TEST_USER_ID,
        DAY,
        WorkTimeShift.MORNING,
        WorkTimeType.LEAVE_WORK_EARLY,
        30,
        note="left for the school run",
    )

    async with db_session_manager.session() as session:
        affect_rows = (await session.exec(select(PtoAffectEntryRecord))).all()

    assert len(affect_rows) == 1
    assert affect_rows[0].note == "left for the school run"


async def test_late_and_early_can_coexist_below_full_shift_duration(
    db_session_manager: DbSessionManager,
) -> None:
    service = _service(db_session_manager)

    late = await service.handle(
        TEST_USER_ID, DAY, WorkTimeShift.MORNING, WorkTimeType.LATE_FOR_WORK, 60
    )
    early = await service.handle(
        TEST_USER_ID, DAY, WorkTimeShift.MORNING, WorkTimeType.LEAVE_WORK_EARLY, 179
    )

    assert late.duration + early.duration == 239


@pytest.mark.parametrize("existing_duration,new_duration", [(200, 40), (200, 41)])
async def test_opposite_types_covering_a_shift_are_rejected(
    db_session_manager: DbSessionManager,
    existing_duration: int,
    new_duration: int,
) -> None:
    service = _service(db_session_manager)
    await service.handle(
        TEST_USER_ID,
        DAY,
        WorkTimeShift.MORNING,
        WorkTimeType.LATE_FOR_WORK,
        existing_duration,
    )

    with pytest.raises(AppException) as exc_info:
        await service.handle(
            TEST_USER_ID,
            DAY,
            WorkTimeShift.MORNING,
            WorkTimeType.LEAVE_WORK_EARLY,
            new_duration,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "work_time_overlaps"
    assert str(DAY) in exc_info.value.detail


async def test_same_type_is_rejected_only_in_the_same_shift(
    db_session_manager: DbSessionManager,
) -> None:
    service = _service(db_session_manager)
    await service.handle(
        TEST_USER_ID,
        DAY,
        WorkTimeShift.MORNING,
        WorkTimeType.LATE_FOR_WORK,
        60,
    )

    with pytest.raises(AppException) as exc_info:
        await service.handle(
            TEST_USER_ID,
            DAY,
            WorkTimeShift.MORNING,
            WorkTimeType.LATE_FOR_WORK,
            30,
        )

    assert exc_info.value.code == "work_time_already_exists"

    afternoon = await service.handle(
        TEST_USER_ID,
        DAY,
        WorkTimeShift.AFTERNOON,
        WorkTimeType.LATE_FOR_WORK,
        60,
    )
    assert afternoon.time == WorkTimeShift.AFTERNOON


async def test_another_owner_work_time_does_not_conflict(
    db_session_manager: DbSessionManager,
) -> None:
    service = _service(db_session_manager)
    await service.handle(
        OTHER_USER_ID,
        DAY,
        WorkTimeShift.MORNING,
        WorkTimeType.LATE_FOR_WORK,
        60,
    )

    work_time = await service.handle(
        TEST_USER_ID,
        DAY,
        WorkTimeShift.MORNING,
        WorkTimeType.LATE_FOR_WORK,
        60,
    )

    assert work_time.type == WorkTimeType.LATE_FOR_WORK


async def test_affect_insert_failure_rolls_back_work_time_entry(
    db_session_manager: DbSessionManager,
) -> None:
    service = CreateWorkTimeService(
        FindPtoAffectEntriesByOwnerAndTypeReader(),
        FindWorkTimeEntriesByIdsAndDateReader(),
        CreateWorkTimeEntryWriter(),
        _FailingAffectWriter(),
        db_session_manager,
    )

    with pytest.raises(RuntimeError, match="force rollback"):
        await service.handle(
            TEST_USER_ID,
            DAY,
            WorkTimeShift.MORNING,
            WorkTimeType.LATE_FOR_WORK,
            60,
        )

    async with db_session_manager.session() as session:
        records = (await session.exec(select(WorkTimeEntryRecord))).all()
        affect_rows = (await session.exec(select(PtoAffectEntryRecord))).all()

    assert records == []
    assert affect_rows == []
