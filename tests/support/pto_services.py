from fastapi import status

from app.core import AppException
from app.database import DbSessionManager
from app.features.attendance.data import (
    CreateMissCheckInEntryWriter,
    FindMissCheckInEntriesByOwnerAndDateRangeReader,
    FindOwnedPtoAttendanceEntriesByDateRangeReader,
    FindWorkdayExceptionsByDatesReader,
    LockAttendanceCalendarWriter,
)
from app.features.attendance.services import (
    CalculateMissCheckInPenaltyService,
    FindMissingCheckInDaysService,
    GetWorkingShiftsService,
)
from app.features.profile.data import FindProfileByUserIdReader
from app.features.pto.data import (
    CreatePtoAffectEntryWriter,
    CreatePtoBankWriter,
    CreatePtoTransactionWriter,
    FindPtoBankByOwnerAndYearReader,
    UpdatePtoBankBalancesWriter,
    UpdatePtoBankSeniorityBalanceWriter,
)
from app.features.pto.entities import PtoBank
from app.features.pto.services import (
    CalculatePtoBalanceDeductionService,
    DeductPtoForEntryService,
    DeductPtoFromBankService,
    GetOrCreatePtoBankService,
    SettleMissCheckInEntriesService,
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
        DeductPtoFromBankService(
            CreatePtoTransactionWriter(),
            UpdatePtoBankBalancesWriter(),
            CalculatePtoBalanceDeductionService(),
        ),
    )


def make_settle_miss_check_in_entries_service(
    create_pto_transaction_writer: CreatePtoTransactionWriter | None = None,
) -> SettleMissCheckInEntriesService:
    return SettleMissCheckInEntriesService(
        FindOwnedPtoAttendanceEntriesByDateRangeReader(),
        FindWorkdayExceptionsByDatesReader(),
        FindMissCheckInEntriesByOwnerAndDateRangeReader(),
        CreateMissCheckInEntryWriter(),
        CreatePtoAffectEntryWriter(),
        DeductPtoFromBankService(
            create_pto_transaction_writer or CreatePtoTransactionWriter(),
            UpdatePtoBankBalancesWriter(),
            CalculatePtoBalanceDeductionService(),
        ),
        FindMissingCheckInDaysService(
            GetWorkingShiftsService(), CalculateMissCheckInPenaltyService()
        ),
    )


def make_get_or_create_pto_bank_service(
    db_session_manager: DbSessionManager,
    create_pto_transaction_writer: CreatePtoTransactionWriter | None = None,
) -> GetOrCreatePtoBankService:
    return GetOrCreatePtoBankService(
        FindPtoBankByOwnerAndYearReader(),
        FindProfileByUserIdReader(),
        CreatePtoBankWriter(),
        UpdatePtoBankSeniorityBalanceWriter(),
        LockAttendanceCalendarWriter(),
        make_settle_miss_check_in_entries_service(create_pto_transaction_writer),
        db_session_manager,
    )


def make_full_deduct_pto_for_entry_service(
    db_session_manager: DbSessionManager,
) -> DeductPtoForEntryService:
    return DeductPtoForEntryService(
        make_get_or_create_pto_bank_service(db_session_manager),
        DeductPtoFromBankService(
            CreatePtoTransactionWriter(),
            UpdatePtoBankBalancesWriter(),
            CalculatePtoBalanceDeductionService(),
        ),
    )
