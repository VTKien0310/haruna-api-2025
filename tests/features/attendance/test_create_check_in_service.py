from datetime import date, time
from uuid import UUID, uuid4

import pytest
from sqlmodel import select

from app.core import AppException
from app.database import (
    CheckInEntryRecord,
    DbSessionManager,
    PtoAffectEntryRecord,
)
from app.features.attendance.data import (
    CreateCheckInEntryWriter,
    FindCheckInEntryByIdsAndDateReader,
)
from app.features.attendance.services import CreateCheckInService
from app.features.pto.data import (
    CreatePtoAffectEntryWriter,
    FindPtoAffectEntriesByOwnerAndTypeReader,
)
from app.features.pto.entities import PtoAffectEntryType
from tests.factories.database_records import TEST_USER_ID

SUNDAY = date(2026, 1, 4)
OTHER_USER_ID = str(uuid4())


def _service(db_session_manager: DbSessionManager) -> CreateCheckInService:
    return CreateCheckInService(
        FindPtoAffectEntriesByOwnerAndTypeReader(),
        FindCheckInEntryByIdsAndDateReader(),
        CreateCheckInEntryWriter(),
        CreatePtoAffectEntryWriter(),
        db_session_manager,
    )


class _FailingAffectWriter:
    async def handle(self, *args: object, **kwargs: object) -> object:
        raise RuntimeError("force rollback")


async def test_drops_seconds_from_the_arrival(
    db_session_manager: DbSessionManager,
) -> None:
    check_in = await _service(db_session_manager).handle(
        TEST_USER_ID, SUNDAY, time(9, 0, 59)
    )

    assert check_in.date == SUNDAY
    assert check_in.time == time(9, 0)


async def test_stores_a_time_given_without_seconds(
    db_session_manager: DbSessionManager,
) -> None:
    check_in = await _service(db_session_manager).handle(
        TEST_USER_ID, SUNDAY, time(7, 15)
    )

    assert check_in.time == time(7, 15, 0)


async def test_stores_the_check_in_and_the_affect_row(
    db_session_manager: DbSessionManager,
) -> None:
    check_in = await _service(db_session_manager).handle(
        TEST_USER_ID, SUNDAY, time(9, 0)
    )

    async with db_session_manager.session() as session:
        stored_check_in = await session.get(CheckInEntryRecord, UUID(check_in.id))
        affect_rows = (await session.exec(select(PtoAffectEntryRecord))).all()

    assert stored_check_in is not None
    assert stored_check_in.date == SUNDAY
    assert stored_check_in.time == time(9, 0)

    assert len(affect_rows) == 1
    affect_row = affect_rows[0]
    assert str(affect_row.owner_id) == TEST_USER_ID
    assert str(affect_row.entry_id) == check_in.id
    assert affect_row.entry_type == PtoAffectEntryType.CHECK_IN.value
    assert affect_row.no_deduction == 0
    assert affect_row.note == ""


async def test_stores_an_optional_affect_note(
    db_session_manager: DbSessionManager,
) -> None:
    await _service(db_session_manager).handle(
        TEST_USER_ID, SUNDAY, time(9, 0), note="arrived after the train"
    )

    async with db_session_manager.session() as session:
        affect_rows = (await session.exec(select(PtoAffectEntryRecord))).all()

    assert len(affect_rows) == 1
    assert affect_rows[0].note == "arrived after the train"


async def test_a_second_check_in_on_the_same_date_is_rejected(
    db_session_manager: DbSessionManager,
) -> None:
    await _service(db_session_manager).handle(TEST_USER_ID, SUNDAY, time(9, 0))

    with pytest.raises(AppException) as exc_info:
        await _service(db_session_manager).handle(TEST_USER_ID, SUNDAY, time(10, 30))

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "check_in_already_exists"

    async with db_session_manager.session() as session:
        check_ins = (await session.exec(select(CheckInEntryRecord))).all()

    assert len(check_ins) == 1
    assert check_ins[0].time == time(9, 0)


async def test_another_caller_can_check_in_on_the_same_date(
    db_session_manager: DbSessionManager,
) -> None:
    await _service(db_session_manager).handle(TEST_USER_ID, SUNDAY, time(9, 0))

    check_in = await _service(db_session_manager).handle(
        OTHER_USER_ID, SUNDAY, time(8, 45)
    )

    assert check_in.time == time(8, 45)

    async with db_session_manager.session() as session:
        check_ins = (await session.exec(select(CheckInEntryRecord))).all()
        affect_rows = (await session.exec(select(PtoAffectEntryRecord))).all()

    assert len(check_ins) == 2
    assert len(affect_rows) == 2


async def test_a_failing_affect_insert_rolls_back_the_check_in(
    db_session_manager: DbSessionManager,
) -> None:
    service = CreateCheckInService(
        FindPtoAffectEntriesByOwnerAndTypeReader(),
        FindCheckInEntryByIdsAndDateReader(),
        CreateCheckInEntryWriter(),
        _FailingAffectWriter(),
        db_session_manager,
    )

    with pytest.raises(RuntimeError, match="force rollback"):
        await service.handle(TEST_USER_ID, SUNDAY, time(9, 0))

    async with db_session_manager.session() as session:
        check_ins = (await session.exec(select(CheckInEntryRecord))).all()
        affect_rows = (await session.exec(select(PtoAffectEntryRecord))).all()

    assert check_ins == []
    assert affect_rows == []
