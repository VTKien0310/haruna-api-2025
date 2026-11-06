from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import PtoBankRecord
from app.features.pto.entities import PtoBank


class FindPtoBankByOwnerAndYearReader:
    async def handle(
        self,
        db_session: AsyncSession,
        owner_id: str,
        year: int,
    ) -> PtoBank | None:
        statement = (
            select(PtoBankRecord)
            .where(PtoBankRecord.owner_id == UUID(owner_id))
            .where(PtoBankRecord.year == year)
            .limit(1)
        )
        result = await db_session.exec(statement)
        record = result.first()

        return PtoBank.from_db_record(record) if record is not None else None


FindPtoBankByOwnerAndYearReaderDep = Annotated[
    FindPtoBankByOwnerAndYearReader, Depends()
]
