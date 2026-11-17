from datetime import date
from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import MissCheckInEntryRecord
from app.features.attendance.entities import MissCheckInEntry


class CreateMissCheckInEntryWriter:
    async def handle(
        self,
        session: AsyncSession,
        day: date,
        penalty: int,
    ) -> MissCheckInEntry:
        record = MissCheckInEntryRecord(date=day, penalty=penalty)
        session.add(record)
        await session.flush()
        return MissCheckInEntry.from_db_record(record)


CreateMissCheckInEntryWriterDep = Annotated[CreateMissCheckInEntryWriter, Depends()]
