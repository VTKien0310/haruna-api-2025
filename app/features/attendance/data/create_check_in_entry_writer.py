from datetime import date, time
from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import CheckInEntryRecord
from app.features.attendance.entities import CheckInEntry


class CreateCheckInEntryWriter:
    async def handle(
        self,
        db_session: AsyncSession,
        day: date,
        arrival: time,
    ) -> CheckInEntry:
        record = CheckInEntryRecord(date=day, time=arrival)
        db_session.add(record)
        await db_session.flush()

        return CheckInEntry.from_db_record(record)


CreateCheckInEntryWriterDep = Annotated[CreateCheckInEntryWriter, Depends()]
