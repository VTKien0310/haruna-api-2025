from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import WorkTimeEntryRecord
from app.features.attendance.entities import WorkTimeEntry


class FindWorkTimeEntriesByIdsAndDateReader:
    async def handle(
        self,
        db_session: AsyncSession,
        entry_ids: list[str],
        day: date,
    ) -> list[WorkTimeEntry]:
        if not entry_ids:
            return []

        statement = select(WorkTimeEntryRecord).where(
            WorkTimeEntryRecord.id.in_([UUID(entry_id) for entry_id in entry_ids]),
            WorkTimeEntryRecord.date == day,
        )
        result = await db_session.exec(statement)

        return [WorkTimeEntry.from_db_record(record) for record in result.all()]


FindWorkTimeEntriesByIdsAndDateReaderDep = Annotated[
    FindWorkTimeEntriesByIdsAndDateReader, Depends()
]
