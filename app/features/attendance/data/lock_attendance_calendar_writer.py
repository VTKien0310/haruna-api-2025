from typing import Annotated

from fastapi import Depends
from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession


class LockAttendanceCalendarWriter:
    async def handle(self, session: AsyncSession, *, exclusive: bool = False) -> None:
        if session.get_bind().dialect.name == "postgresql":
            # Separate two-integer namespace from the bigint PTO owner locks.
            lock = (
                func.pg_advisory_xact_lock
                if exclusive
                else func.pg_advisory_xact_lock_shared
            )
            await session.exec(select(lock(0x4852554E, 1)))


LockAttendanceCalendarWriterDep = Annotated[LockAttendanceCalendarWriter, Depends()]
