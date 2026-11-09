from datetime import date
from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import WorkTimeEntryRecord
from app.features.attendance.entities import (
    WorkTimeEntry,
    WorkTimeShift,
    WorkTimeType,
)


class CreateWorkTimeEntryWriter:
    async def handle(
        self,
        db_session: AsyncSession,
        day: date,
        shift: WorkTimeShift,
        entry_type: WorkTimeType,
        duration: int,
    ) -> WorkTimeEntry:
        record = WorkTimeEntryRecord(
            date=day,
            time=int(shift),
            type=int(entry_type),
            duration=duration,
        )
        db_session.add(record)
        await db_session.flush()

        return WorkTimeEntry.from_db_record(record)


CreateWorkTimeEntryWriterDep = Annotated[CreateWorkTimeEntryWriter, Depends()]
