from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import PtoAffectEntryRecord
from app.features.pto.entities import PtoAffectEntry


class UpdatePtoAffectEntryWriter:
    async def handle(self, db_session: AsyncSession, entry: PtoAffectEntry) -> None:
        record = await db_session.get(PtoAffectEntryRecord, UUID(entry.id))
        if record is None:
            raise RuntimeError("Locked PTO affect entry disappeared")
        record.no_deduction = int(entry.no_deduction)
        record.note = entry.note
        record.updated_at = datetime.now(timezone.utc)
        await db_session.flush()


UpdatePtoAffectEntryWriterDep = Annotated[UpdatePtoAffectEntryWriter, Depends()]
