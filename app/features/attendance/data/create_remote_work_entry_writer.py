from datetime import date
from typing import Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import RemoteWorkEntryRecord
from app.features.attendance.entities import RemoteWorkEntry, RemoteWorkType


class CreateRemoteWorkEntryWriter:
    async def handle(
        self,
        db_session: AsyncSession,
        day: date,
        entry_type: RemoteWorkType,
    ) -> RemoteWorkEntry:
        record = RemoteWorkEntryRecord(date=day, type=int(entry_type))
        db_session.add(record)
        await db_session.flush()

        return RemoteWorkEntry.from_db_record(record)


CreateRemoteWorkEntryWriterDep = Annotated[CreateRemoteWorkEntryWriter, Depends()]
