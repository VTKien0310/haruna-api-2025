from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import LeaveWorkEntryRecord
from app.features.attendance.entities import LeaveWorkEntry


class UpdateLeaveWorkEntryWriter:
    async def handle(self, db_session: AsyncSession, entry: LeaveWorkEntry) -> None:
        record = await db_session.get(LeaveWorkEntryRecord, UUID(entry.id))
        if record is None:
            raise RuntimeError("Locked attendance entry disappeared")
        record.date = entry.date
        record.start = entry.start
        record.end = entry.end
        await db_session.flush()


UpdateLeaveWorkEntryWriterDep = Annotated[UpdateLeaveWorkEntryWriter, Depends()]
