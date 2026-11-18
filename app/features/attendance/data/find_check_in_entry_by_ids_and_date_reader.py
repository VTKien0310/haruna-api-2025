from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import CheckInEntryRecord
from app.features.attendance.entities import CheckInEntry


class FindCheckInEntryByIdsAndDateReader:
    async def handle(
        self,
        db_session: AsyncSession,
        entry_ids: list[str],
        day: date,
    ) -> CheckInEntry | None:
        if not entry_ids:
            return None

        statement = (
            select(CheckInEntryRecord)
            .where(
                CheckInEntryRecord.id.in_([UUID(entry_id) for entry_id in entry_ids])
            )
            .where(CheckInEntryRecord.date == day)
            .limit(1)
        )
        result = await db_session.exec(statement)
        record = result.first()

        return CheckInEntry.from_db_record(record) if record is not None else None


FindCheckInEntryByIdsAndDateReaderDep = Annotated[
    FindCheckInEntryByIdsAndDateReader, Depends()
]
