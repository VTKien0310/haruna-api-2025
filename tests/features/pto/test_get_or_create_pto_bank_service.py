from datetime import date, datetime
from uuid import UUID

import pytest
from sqlmodel import SQLModel

from app.core import AppException
from app.database import DbSessionManager, PtoBankRecord
from app.features.profile.data import FindProfileByUserIdReader
from app.features.pto.constants import MINUTES_PER_WORK_DAY
from app.features.pto.data import (
    CreatePtoBankWriter,
    FindPtoBankByOwnerAndYearReader,
    UpdatePtoBankSeniorityBalanceWriter,
)
from app.features.pto.services import GetOrCreatePtoBankService
from tests.factories.database_records import (
    TEST_PTO_BANK_ID,
    TEST_USER_ID,
    make_profile_record,
    make_pto_bank_record,
)

PREVIOUS_YEAR_BANK_ID = UUID("44444444-4444-4444-8444-444444444444")


def _service(db_session_manager: DbSessionManager) -> GetOrCreatePtoBankService:
    return GetOrCreatePtoBankService(
        FindPtoBankByOwnerAndYearReader(),
        FindProfileByUserIdReader(),
        CreatePtoBankWriter(),
        UpdatePtoBankSeniorityBalanceWriter(),
        db_session_manager,
    )


async def _add_records(
    db_session_manager: DbSessionManager, *records: SQLModel
) -> None:
    async with db_session_manager.transaction() as session:
        for record in records:
            session.add(record)


async def _get_bank(
    db_session_manager: DbSessionManager, bank_id: UUID
) -> PtoBankRecord | None:
    async with db_session_manager.session() as session:
        return await session.get(PtoBankRecord, bank_id)


def _work_start_years_ago(years: int) -> date:
    today = date.today()
    try:
        return today.replace(year=today.year - years)
    except ValueError:  # February 29
        return today.replace(year=today.year - years, day=28)


async def test_creates_current_year_bank_with_default_balances(
    db_session_manager: DbSessionManager,
) -> None:
    current_year = date.today().year
    await _add_records(
        db_session_manager,
        make_profile_record(work_start_date=date(2020, 6, 15)),
    )

    bank = await _service(db_session_manager).handle(TEST_USER_ID, current_year)

    assert bank.owner_id == TEST_USER_ID
    assert bank.year == current_year
    assert bank.annual_balance == 13 * MINUTES_PER_WORK_DAY
    assert bank.extended_balance == 0
    assert (
        bank.seniority_balance
        == min(date.today().year - 2020, 8) * MINUTES_PER_WORK_DAY
    )
    assert bank.original_annual_balance == bank.annual_balance
    assert bank.original_extended_balance == bank.extended_balance
    assert bank.original_seniority_balance == bank.seniority_balance
    stored = await _get_bank(db_session_manager, UUID(bank.id))
    assert stored is not None
    assert (
        stored.original_annual_balance == stored.annual_balance == bank.annual_balance
    )
    assert (
        stored.original_extended_balance
        == stored.extended_balance
        == bank.extended_balance
    )
    assert (
        stored.original_seniority_balance
        == stored.seniority_balance
        == bank.seniority_balance
    )


async def test_creates_bank_with_extended_balance_from_last_year(
    db_session_manager: DbSessionManager,
) -> None:
    current_year = date.today().year
    await _add_records(
        db_session_manager,
        make_profile_record(),
        make_pto_bank_record(
            id=PREVIOUS_YEAR_BANK_ID,
            year=current_year - 1,
            annual_balance=100,
            seniority_balance=50,
            original_annual_balance=900,
            original_seniority_balance=800,
        ),
    )

    bank = await _service(db_session_manager).handle(TEST_USER_ID, current_year)

    assert bank.extended_balance == 150
    assert bank.original_extended_balance == bank.extended_balance
    stored = await _get_bank(db_session_manager, UUID(bank.id))
    assert stored is not None
    assert stored.extended_balance == stored.original_extended_balance == 150


async def test_creates_bank_with_seniority_capped_at_eight_days(
    db_session_manager: DbSessionManager,
) -> None:
    await _add_records(
        db_session_manager,
        make_profile_record(work_start_date=_work_start_years_ago(10)),
    )

    bank = await _service(db_session_manager).handle(TEST_USER_ID, date.today().year)

    assert bank.seniority_balance == 8 * MINUTES_PER_WORK_DAY
    assert bank.original_seniority_balance == bank.seniority_balance
    stored = await _get_bank(db_session_manager, UUID(bank.id))
    assert stored is not None
    assert stored.original_seniority_balance == stored.seniority_balance


async def test_creating_past_or_future_year_is_not_allowed(
    db_session_manager: DbSessionManager,
) -> None:
    await _add_records(db_session_manager, make_profile_record())
    current_year = date.today().year

    for year in (current_year - 1, current_year + 1):
        with pytest.raises(AppException) as exc_info:
            await _service(db_session_manager).handle(TEST_USER_ID, year)
        assert exc_info.value.status_code == 404
        assert exc_info.value.code == "pto_bank_not_found"


async def test_creation_requires_a_profile(
    db_session_manager: DbSessionManager,
) -> None:
    with pytest.raises(AppException) as exc_info:
        await _service(db_session_manager).handle(TEST_USER_ID, date.today().year)

    assert exc_info.value.status_code == 404
    assert exc_info.value.code == "profile_not_found"


async def test_viewing_past_year_returns_the_record_unchanged(
    db_session_manager: DbSessionManager,
) -> None:
    unchanged_timestamp = datetime(2026, 1, 1)
    await _add_records(
        db_session_manager,
        make_profile_record(work_start_date=date(2010, 1, 1)),
        make_pto_bank_record(
            id=TEST_PTO_BANK_ID,
            year=date.today().year - 1,
            seniority_balance=0,
            updated_at=unchanged_timestamp,
            original_annual_balance=111,
            original_extended_balance=222,
            original_seniority_balance=333,
        ),
    )

    bank = await _service(db_session_manager).handle(
        TEST_USER_ID, date.today().year - 1
    )

    assert bank.id == str(TEST_PTO_BANK_ID)
    assert bank.seniority_balance == 0
    assert (
        bank.original_annual_balance,
        bank.original_extended_balance,
        bank.original_seniority_balance,
    ) == (111, 222, 333)
    stored = await _get_bank(db_session_manager, TEST_PTO_BANK_ID)
    assert stored is not None
    assert stored.seniority_balance == 0
    assert (
        stored.original_annual_balance,
        stored.original_extended_balance,
        stored.original_seniority_balance,
    ) == (111, 222, 333)
    assert stored.updated_at == unchanged_timestamp


async def test_viewing_current_year_accrues_seniority_and_persists(
    db_session_manager: DbSessionManager,
) -> None:
    await _add_records(
        db_session_manager,
        make_profile_record(work_start_date=_work_start_years_ago(2)),
        make_pto_bank_record(
            id=TEST_PTO_BANK_ID,
            year=date.today().year,
            seniority_balance=MINUTES_PER_WORK_DAY,
            original_annual_balance=444,
            original_extended_balance=555,
            original_seniority_balance=666,
        ),
    )

    bank = await _service(db_session_manager).handle(TEST_USER_ID, date.today().year)

    assert bank.seniority_balance == 2 * MINUTES_PER_WORK_DAY
    assert (
        bank.original_annual_balance,
        bank.original_extended_balance,
        bank.original_seniority_balance,
    ) == (444, 555, 666)
    stored = await _get_bank(db_session_manager, TEST_PTO_BANK_ID)
    assert stored is not None
    assert stored.seniority_balance == 2 * MINUTES_PER_WORK_DAY
    assert (
        stored.original_annual_balance,
        stored.original_extended_balance,
        stored.original_seniority_balance,
    ) == (444, 555, 666)


async def test_viewing_current_year_does_not_accrue_before_the_anniversary(
    db_session_manager: DbSessionManager,
) -> None:
    unchanged_timestamp = datetime(2026, 1, 1)
    await _add_records(
        db_session_manager,
        make_profile_record(work_start_date=_work_start_years_ago(2)),
        make_pto_bank_record(
            id=TEST_PTO_BANK_ID,
            year=date.today().year,
            seniority_balance=2 * MINUTES_PER_WORK_DAY,
            updated_at=unchanged_timestamp,
        ),
    )

    bank = await _service(db_session_manager).handle(TEST_USER_ID, date.today().year)

    assert bank.seniority_balance == 2 * MINUTES_PER_WORK_DAY
    stored = await _get_bank(db_session_manager, TEST_PTO_BANK_ID)
    assert stored is not None
    assert stored.updated_at == unchanged_timestamp
