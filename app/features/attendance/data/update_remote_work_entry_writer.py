from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import RemoteWorkEntryRecord
from app.features.attendance.entities import RemoteWorkEntry


class UpdateRemoteWorkEntryWriter:
    async def handle(self, db_session: AsyncSession, entry: RemoteWorkEntry) -> None:
        record = await db_session.get(RemoteWorkEntryRecord, UUID(entry.id))
        if record is None:
            raise RuntimeError("Locked attendance entry disappeared")
        record.date = entry.date
        record.type = entry.type
        await db_session.flush()


UpdateRemoteWorkEntryWriterDep = Annotated[UpdateRemoteWorkEntryWriter, Depends()]
