from datetime import date
from uuid import UUID, uuid4

import pytest
from sqlmodel import select

from app.core import AppException
from app.database import DbSessionManager, PtoAffectEntryRecord, RemoteWorkEntryRecord
from app.features.attendance.data import (
    CreateRemoteWorkEntryWriter,
    CreateTimeOffEntryWriter,
    FindRemoteWorkEntriesByIdsAndDateReader,
    FindTimeOffEntriesByIdsAndDatesReader,
)
from app.features.attendance.entities import RemoteWorkType, TimeOffType
from app.features.attendance.services import (
    CreateRemoteWorkService,
    CreateTimeOffService,
)
from app.features.pto.data import (
    CreatePtoAffectEntryWriter,
    FindPtoAffectEntriesByOwnerAndTypeReader,
)
from app.features.pto.entities import PtoAffectEntryType
from tests.factories.database_records import TEST_USER_ID

DAY = date(2026, 1, 5)
OTHER_USER_ID = str(uuid4())


def _service(db_session_manager: DbSessionManager) -> CreateRemoteWorkService:
    return CreateRemoteWorkService(
        FindPtoAffectEntriesByOwnerAndTypeReader(),
        FindRemoteWorkEntriesByIdsAndDateReader(),
        CreateRemoteWorkEntryWriter(),
        CreatePtoAffectEntryWriter(),
        db_session_manager,
    )


class _FailingAffectWriter:
    async def handle(self, *args: object, **kwargs: object) -> object:
        raise RuntimeError("force rollback")


async def test_stores_remote_work_and_its_affect_row(
    db_session_manager: DbSessionManager,
) -> None:
    remote_work = await _service(db_session_manager).handle(
        TEST_USER_ID, DAY, RemoteWorkType.MORNING
    )

    assert remote_work.date == DAY
    assert remote_work.type == RemoteWorkType.MORNING

    async with db_session_manager.session() as session:
        record = await session.get(RemoteWorkEntryRecord, UUID(remote_work.id))
        affect_rows = (await session.exec(select(PtoAffectEntryRecord))).all()

    assert record is not None
    assert record.date == DAY
    assert record.type == RemoteWorkType.MORNING
    assert len(affect_rows) == 1
    assert str(affect_rows[0].owner_id) == TEST_USER_ID
    assert str(affect_rows[0].entry_id) == remote_work.id
    assert affect_rows[0].entry_type == PtoAffectEntryType.REMOTE_WORK.value
    assert affect_rows[0].no_deduction == 1


async def test_morning_and_afternoon_remote_work_can_coexist(
    db_session_manager: DbSessionManager,
) -> None:
    service = _service(db_session_manager)

    morning = await service.handle(TEST_USER_ID, DAY, RemoteWorkType.MORNING)
    afternoon = await service.handle(TEST_USER_ID, DAY, RemoteWorkType.AFTERNOON)

    assert morning.type == RemoteWorkType.MORNING
    assert afternoon.type == RemoteWorkType.AFTERNOON


@pytest.mark.parametrize(
    ("existing_type", "new_type"),
    [
        (RemoteWorkType.FULL_DAY, RemoteWorkType.MORNING),
        (RemoteWorkType.AFTERNOON, RemoteWorkType.FULL_DAY),
        (RemoteWorkType.MORNING, RemoteWorkType.MORNING),
    ],
)
async def test_conflicting_remote_work_is_rejected(
    db_session_manager: DbSessionManager,
    existing_type: RemoteWorkType,
    new_type: RemoteWorkType,
) -> None:
    service = _service(db_session_manager)
    await service.handle(TEST_USER_ID, DAY, existing_type)

    with pytest.raises(AppException) as exc_info:
        await service.handle(TEST_USER_ID, DAY, new_type)

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "remote_work_already_exists"
    assert str(DAY) in exc_info.value.detail


async def test_time_off_does_not_conflict_with_remote_work(
    db_session_manager: DbSessionManager,
) -> None:
    time_off_service = CreateTimeOffService(
        FindPtoAffectEntriesByOwnerAndTypeReader(),
        FindTimeOffEntriesByIdsAndDatesReader(),
        CreateTimeOffEntryWriter(),
        CreatePtoAffectEntryWriter(),
        db_session_manager,
    )
    await time_off_service.handle(TEST_USER_ID, DAY, None, TimeOffType.FULL_DAY)

    remote_work = await _service(db_session_manager).handle(
        TEST_USER_ID, DAY, RemoteWorkType.FULL_DAY
    )

    assert remote_work.type == RemoteWorkType.FULL_DAY


async def test_another_owner_remote_work_does_not_conflict(
    db_session_manager: DbSessionManager,
) -> None:
    service = _service(db_session_manager)
    await service.handle(OTHER_USER_ID, DAY, RemoteWorkType.FULL_DAY)

    remote_work = await service.handle(TEST_USER_ID, DAY, RemoteWorkType.MORNING)

    assert remote_work.type == RemoteWorkType.MORNING


async def test_affect_insert_failure_rolls_back_remote_work_entry(
    db_session_manager: DbSessionManager,
) -> None:
    service = CreateRemoteWorkService(
        FindPtoAffectEntriesByOwnerAndTypeReader(),
        FindRemoteWorkEntriesByIdsAndDateReader(),
        CreateRemoteWorkEntryWriter(),
        _FailingAffectWriter(),
        db_session_manager,
    )

    with pytest.raises(RuntimeError, match="force rollback"):
        await service.handle(TEST_USER_ID, DAY, RemoteWorkType.FULL_DAY)

    async with db_session_manager.session() as session:
        records = (await session.exec(select(RemoteWorkEntryRecord))).all()
        affect_rows = (await session.exec(select(PtoAffectEntryRecord))).all()

    assert records == []
    assert affect_rows == []
