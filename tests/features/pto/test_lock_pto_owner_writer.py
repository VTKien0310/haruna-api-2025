from unittest.mock import create_autospec
from uuid import UUID

from sqlalchemy.dialects import postgresql
from sqlmodel.ext.asyncio.session import AsyncSession

from app.features.pto.data import LockPtoOwnerWriter


async def test_postgres_lock_uses_bound_normalized_owner_without_deprecated_execute() -> (
    None
):
    session = create_autospec(AsyncSession, instance=True)
    session.get_bind.return_value.dialect.name = "postgresql"
    owner_id = "ABCDEFAB-CDEF-4ABC-8DEF-ABCDEFABCDEF"

    await LockPtoOwnerWriter().handle(session, owner_id)

    session.exec.assert_awaited_once()
    session.execute.assert_not_called()
    statement = session.exec.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "pg_advisory_xact_lock" in sql
    assert "hashtextextended" in sql
    assert str(UUID(owner_id)) not in sql
    assert set(compiled.params.values()) == {str(UUID(owner_id)), 0}


async def test_sqlite_does_not_execute_a_postgres_lock() -> None:
    session = create_autospec(AsyncSession, instance=True)
    session.get_bind.return_value.dialect.name = "sqlite"

    await LockPtoOwnerWriter().handle(session, "abcdefab-cdef-4abc-8def-abcdefabcdef")

    session.exec.assert_not_called()
    session.execute.assert_not_called()
