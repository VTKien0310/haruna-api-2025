from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import PtoAffectEntryRecord
from app.features.pto.entities import PtoAffectEntry, PtoAffectEntryType

from .lock_pto_owner_writer import LockPtoOwnerWriter


class FindPtoAffectEntriesByOwnerAndTypeReader:
    async def handle(
        self,
        db_session: AsyncSession,
        owner_id: str,
        entry_type: PtoAffectEntryType,
    ) -> list[PtoAffectEntry]:
        await LockPtoOwnerWriter().handle(db_session, owner_id)
        statement = select(PtoAffectEntryRecord).where(
            PtoAffectEntryRecord.owner_id == UUID(owner_id),
            PtoAffectEntryRecord.entry_type == entry_type.value,
        )
        result = await db_session.exec(statement)

        return [PtoAffectEntry.from_db_record(record) for record in result.all()]


FindPtoAffectEntriesByOwnerAndTypeReaderDep = Annotated[
    FindPtoAffectEntriesByOwnerAndTypeReader, Depends()
]
