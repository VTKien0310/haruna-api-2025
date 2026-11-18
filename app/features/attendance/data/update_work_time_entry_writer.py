from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import WorkTimeEntryRecord
from app.features.attendance.entities import WorkTimeEntry


class UpdateWorkTimeEntryWriter:
    async def handle(self, db_session: AsyncSession, entry: WorkTimeEntry) -> None:
        record = await db_session.get(WorkTimeEntryRecord, UUID(entry.id))
        if record is None:
            raise RuntimeError("Locked attendance entry disappeared")
        record.date = entry.date
        record.time = entry.time
        record.type = entry.type
        record.duration = entry.duration
        await db_session.flush()


UpdateWorkTimeEntryWriterDep = Annotated[UpdateWorkTimeEntryWriter, Depends()]
