from datetime import date, time
from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import LeaveWorkEntryRecord
from app.features.attendance.entities import LeaveWorkEntry


class CreateLeaveWorkEntryWriter:
    async def handle(
        self,
        db_session: AsyncSession,
        day: date,
        start: time,
        end: time,
    ) -> LeaveWorkEntry:
        record = LeaveWorkEntryRecord(date=day, start=start, end=end)
        db_session.add(record)
        await db_session.flush()

        return LeaveWorkEntry.from_db_record(record)


CreateLeaveWorkEntryWriterDep = Annotated[CreateLeaveWorkEntryWriter, Depends()]
