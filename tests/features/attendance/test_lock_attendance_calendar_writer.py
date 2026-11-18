from unittest.mock import create_autospec

import pytest
from sqlalchemy.dialects import postgresql
from sqlmodel.ext.asyncio.session import AsyncSession

from app.features.attendance.data import LockAttendanceCalendarWriter


@pytest.mark.parametrize("exclusive", [False, True])
async def test_postgres_calendar_lock_uses_shared_namespace(exclusive: bool) -> None:
    session = create_autospec(AsyncSession, instance=True)
    session.get_bind.return_value.dialect.name = "postgresql"
    await LockAttendanceCalendarWriter().handle(session, exclusive=exclusive)
    session.exec.assert_awaited_once()
    statement = session.exec.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    expected = (
        "pg_advisory_xact_lock(" if exclusive else "pg_advisory_xact_lock_shared("
    )
    assert expected in str(compiled)
    assert set(compiled.params.values()) == {0x4852554E, 1}


async def test_sqlite_does_not_execute_calendar_lock() -> None:
    session = create_autospec(AsyncSession, instance=True)
    session.get_bind.return_value.dialect.name = "sqlite"
    await LockAttendanceCalendarWriter().handle(session, exclusive=True)
    session.exec.assert_not_called()
