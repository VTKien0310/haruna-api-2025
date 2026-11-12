from fastapi import status

from app.core import AppException
from app.database import DbSessionManager
from app.features.profile.data import FindProfileByUserIdReader
from app.features.pto.data import (
    CreatePtoBankWriter,
    CreatePtoTransactionWriter,
    FindPtoBankByOwnerAndYearReader,
    UpdatePtoBankBalancesWriter,
    UpdatePtoBankSeniorityBalanceWriter,
)
from app.features.pto.entities import PtoBank
from app.features.pto.services import (
    DeductPtoForEntryService,
    GetOrCreatePtoBankService,
)


class NoopDeductPtoForEntryService:
    async def handle(self, *args: object, **kwargs: object) -> None:
        return None


class _StaticGetOrCreatePtoBankService:
    def __init__(self, db_session_manager: DbSessionManager) -> None:
        self.__db_session_manager = db_session_manager

    async def handle_with_session(
        self,
        db_session: object,
        user_id: str,
        year: int,
    ) -> PtoBank:
        bank = await FindPtoBankByOwnerAndYearReader().handle(
            db_session,  # type: ignore[arg-type]
            user_id,
            year,
        )
        if bank is None:
            raise AppException(
                status_code=status.HTTP_404_NOT_FOUND,
                code="pto_bank_not_found",
                message=f"PTO bank for year '{year}' not found",
            )
        return bank


def make_deduct_pto_for_entry_service(
    db_session_manager: DbSessionManager,
) -> DeductPtoForEntryService:
    return DeductPtoForEntryService(
        _StaticGetOrCreatePtoBankService(db_session_manager),  # type: ignore[arg-type]
        CreatePtoTransactionWriter(),
        UpdatePtoBankBalancesWriter(),
    )


def make_full_deduct_pto_for_entry_service(
    db_session_manager: DbSessionManager,
) -> DeductPtoForEntryService:
    return DeductPtoForEntryService(
        GetOrCreatePtoBankService(
            FindPtoBankByOwnerAndYearReader(),
            FindProfileByUserIdReader(),
            CreatePtoBankWriter(),
            UpdatePtoBankSeniorityBalanceWriter(),
            db_session_manager,
        ),
        CreatePtoTransactionWriter(),
        UpdatePtoBankBalancesWriter(),
    )
