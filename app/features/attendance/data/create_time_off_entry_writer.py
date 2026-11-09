from datetime import date
from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import TimeOffEntryRecord
from app.features.attendance.entities import TimeOffEntry, TimeOffType


class CreateTimeOffEntryWriter:
    async def handle(
        self,
        db_session: AsyncSession,
        day: date,
        entry_type: TimeOffType,
    ) -> TimeOffEntry:
        record = TimeOffEntryRecord(date=day, type=int(entry_type))
        db_session.add(record)
        await db_session.flush()

        return TimeOffEntry.from_db_record(record)


CreateTimeOffEntryWriterDep = Annotated[CreateTimeOffEntryWriter, Depends()]
