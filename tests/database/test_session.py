import pytest

from app.database import DbSessionManager, PtoBankRecord
from tests.factories.database_records import TEST_PTO_BANK_ID, make_pto_bank_record


async def test_transaction_commits_on_success(
    db_session_manager: DbSessionManager,
) -> None:
    async with db_session_manager.transaction() as session:
        session.add(make_pto_bank_record())
        await session.flush()

    async with db_session_manager.session() as session:
        stored = await session.get(PtoBankRecord, TEST_PTO_BANK_ID)

    assert stored is not None
    assert stored.id == TEST_PTO_BANK_ID


async def test_transaction_rolls_back_flushed_writes_on_exception(
    db_session_manager: DbSessionManager,
) -> None:
    with pytest.raises(RuntimeError, match="force rollback"):
        async with db_session_manager.transaction() as session:
            session.add(make_pto_bank_record())
            await session.flush()
            raise RuntimeError("force rollback")

    async with db_session_manager.session() as session:
        stored = await session.get(PtoBankRecord, TEST_PTO_BANK_ID)

    assert stored is None
