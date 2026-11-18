from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import CheckInEntryRecord
from app.features.attendance.entities import CheckInEntry


class UpdateCheckInEntryWriter:
    async def handle(self, db_session: AsyncSession, entry: CheckInEntry) -> None:
        record = await db_session.get(CheckInEntryRecord, UUID(entry.id))
        if record is None:
            raise RuntimeError("Locked attendance entry disappeared")
        record.date = entry.date
        record.time = entry.time
        await db_session.flush()


UpdateCheckInEntryWriterDep = Annotated[UpdateCheckInEntryWriter, Depends()]
