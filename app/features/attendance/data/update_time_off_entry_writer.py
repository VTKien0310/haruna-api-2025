from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import TimeOffEntryRecord
from app.features.attendance.entities import TimeOffEntry


class UpdateTimeOffEntryWriter:
    async def handle(self, db_session: AsyncSession, entry: TimeOffEntry) -> None:
        record = await db_session.get(TimeOffEntryRecord, UUID(entry.id))
        if record is None:
            raise RuntimeError("Locked attendance entry disappeared")
        record.date = entry.date
        record.type = entry.type
        await db_session.flush()


UpdateTimeOffEntryWriterDep = Annotated[UpdateTimeOffEntryWriter, Depends()]
