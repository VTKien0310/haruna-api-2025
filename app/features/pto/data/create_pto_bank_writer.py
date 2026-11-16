from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import PtoBankRecord
from app.features.pto.entities import PtoBank


class CreatePtoBankWriter:
    async def handle(
        self,
        db_session: AsyncSession,
        owner_id: str,
        year: int,
        annual_balance: int,
        extended_balance: int,
        seniority_balance: int,
        original_annual_balance: int,
        original_extended_balance: int,
        original_seniority_balance: int,
    ) -> PtoBank:
        record = PtoBankRecord(
            owner_id=UUID(owner_id),
            year=year,
            annual_balance=annual_balance,
            extended_balance=extended_balance,
            seniority_balance=seniority_balance,
            original_annual_balance=original_annual_balance,
            original_extended_balance=original_extended_balance,
            original_seniority_balance=original_seniority_balance,
        )
        db_session.add(record)
        await db_session.flush()

        return PtoBank.from_db_record(record)


CreatePtoBankWriterDep = Annotated[CreatePtoBankWriter, Depends()]
