from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import RemoteWorkEntryRecord
from app.features.attendance.entities import RemoteWorkEntry


class FindRemoteWorkEntriesByIdsAndDateReader:
    async def handle(
        self,
        db_session: AsyncSession,
        entry_ids: list[str],
        day: date,
    ) -> list[RemoteWorkEntry]:
        if not entry_ids:
            return []

        statement = select(RemoteWorkEntryRecord).where(
            RemoteWorkEntryRecord.id.in_([UUID(entry_id) for entry_id in entry_ids]),
            RemoteWorkEntryRecord.date == day,
        )
        result = await db_session.exec(statement)

        return [RemoteWorkEntry.from_db_record(record) for record in result.all()]


FindRemoteWorkEntriesByIdsAndDateReaderDep = Annotated[
    FindRemoteWorkEntriesByIdsAndDateReader, Depends()
]
