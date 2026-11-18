from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import PtoBankRecord
from app.features.pto.entities import PtoBank


class UpdatePtoBankBalancesWriter:
    async def handle(
        self,
        db_session: AsyncSession,
        bank: PtoBank,
    ) -> None:
        record = await db_session.get(PtoBankRecord, UUID(bank.id))
        if record is None:
            return

        record.annual_balance = bank.annual_balance
        record.extended_balance = bank.extended_balance
        record.seniority_balance = bank.seniority_balance
        record.updated_at = datetime.now(timezone.utc)
        await db_session.flush()


UpdatePtoBankBalancesWriterDep = Annotated[UpdatePtoBankBalancesWriter, Depends()]
