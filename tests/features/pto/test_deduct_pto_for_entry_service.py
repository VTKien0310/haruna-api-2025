from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlmodel import SQLModel, select

from app.core import AppException
from app.database import (
    DbSessionManager,
    PtoAffectEntryRecord,
    PtoBankRecord,
    PtoTransactionRecord,
)
from app.features.pto.entities import (
    PtoAffectEntry,
    PtoAffectEntryType,
    PtoTransactionType,
)
from app.features.pto.services import DeductPtoForEntryService
from tests.factories.database_records import (
    TEST_USER_ID,
    TEST_USER_UUID,
    make_pto_bank_record,
    make_profile_record,
)
from tests.support.pto_services import (
    make_deduct_pto_for_entry_service,
    make_full_deduct_pto_for_entry_service,
)

NOW = datetime(2026, 1, 5, 8, 0, tzinfo=timezone.utc)


def _affect_entry(
    no_deduction: bool = False,
    entry_type: PtoAffectEntryType | None = PtoAffectEntryType.TIME_OFF,
) -> PtoAffectEntry:
    return PtoAffectEntry(
        id=str(uuid4()),
        owner_id=TEST_USER_ID,
        entry_id=str(uuid4()),
        entry_type=entry_type,
        no_deduction=no_deduction,
        note="",
        created_at=NOW,
        updated_at=NOW,
    )


def _pto_bank_record(**overrides: object) -> PtoBankRecord:
    balances = {
        "year": 2026,
        "extended_balance": 0,
        "seniority_balance": 0,
        "annual_balance": 0,
        "updated_at": datetime(2026, 1, 1),
    }
    balances.update(overrides)
    balances["original_extended_balance"] = balances["extended_balance"]
    balances["original_seniority_balance"] = balances["seniority_balance"]
    balances["original_annual_balance"] = balances["annual_balance"]
    return make_pto_bank_record(**balances)


async def _run(
    db_session_manager: DbSessionManager,
    affect_entry: PtoAffectEntry,
    deduction_minutes: int,
    year: int = 2026,
    service: DeductPtoForEntryService | None = None,
):
    service = service or make_deduct_pto_for_entry_service(db_session_manager)
    async with db_session_manager.transaction() as session:
        session.add(
            PtoAffectEntryRecord(
                id=UUID(affect_entry.id),
                owner_id=TEST_USER_UUID,
                entry_id=UUID(affect_entry.entry_id) if affect_entry.entry_id else None,
                entry_type=affect_entry.entry_type.value
                if affect_entry.entry_type
                else None,
                no_deduction=1 if affect_entry.no_deduction else 0,
                note="",
            )
        )
        await session.flush()
        return await service.handle(
            session, TEST_USER_ID, affect_entry, deduction_minutes, year
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


async def _transactions(db_session_manager: DbSessionManager) -> list:
    async with db_session_manager.session() as session:
        return list((await session.exec(select(PtoTransactionRecord))).all())


async def test_deducts_extended_then_seniority_then_annual(
    db_session_manager: DbSessionManager,
) -> None:
    bank_record = _pto_bank_record(
        extended_balance=100,
        seniority_balance=50,
        annual_balance=200,
    )
    await _add_records(db_session_manager, make_profile_record(), bank_record)

    transaction = await _run(db_session_manager, _affect_entry(), 180)

    assert transaction is not None
    assert transaction.cause == "time_off_entries_create"
    assert transaction.type == PtoTransactionType.DECREASE
    assert transaction.value == 180
    assert transaction.exceed_bank_value == 0
    stored = await _get_bank(db_session_manager, UUID(transaction.pto_bank_id))
    assert stored is not None
    assert stored.extended_balance == 0
    assert stored.seniority_balance == 0
    assert stored.annual_balance == 170


async def test_skips_balances_in_order_when_the_first_covers_the_deduction(
    db_session_manager: DbSessionManager,
) -> None:
    bank_record = _pto_bank_record(
        extended_balance=500,
        seniority_balance=50,
        annual_balance=200,
    )
    await _add_records(db_session_manager, make_profile_record(), bank_record)

    transaction = await _run(db_session_manager, _affect_entry(), 480)

    assert transaction is not None
    assert transaction.exceed_bank_value == 0
    stored = await _get_bank(db_session_manager, UUID(transaction.pto_bank_id))
    assert stored is not None
    assert stored.extended_balance == 20
    assert stored.seniority_balance == 50
    assert stored.annual_balance == 200


async def test_records_the_excess_when_all_balances_run_out(
    db_session_manager: DbSessionManager,
) -> None:
    bank_record = _pto_bank_record(
        extended_balance=100,
        seniority_balance=0,
        annual_balance=200,
    )
    await _add_records(db_session_manager, make_profile_record(), bank_record)

    transaction = await _run(db_session_manager, _affect_entry(), 480)

    assert transaction is not None
    assert transaction.value == 480
    assert transaction.exceed_bank_value == 180
    stored = await _get_bank(db_session_manager, UUID(transaction.pto_bank_id))
    assert stored is not None
    assert stored.extended_balance == 0
    assert stored.seniority_balance == 0
    assert stored.annual_balance == 0


async def test_empty_bank_records_the_whole_value_as_excess(
    db_session_manager: DbSessionManager,
) -> None:
    bank_record = _pto_bank_record()
    await _add_records(db_session_manager, make_profile_record(), bank_record)

    transaction = await _run(db_session_manager, _affect_entry(), 240)

    assert transaction is not None
    assert transaction.exceed_bank_value == 240
    stored = await _get_bank(db_session_manager, UUID(transaction.pto_bank_id))
    assert stored is not None
    assert stored.annual_balance == 0


async def test_no_deduction_creates_no_transaction(
    db_session_manager: DbSessionManager,
) -> None:
    bank_record = _pto_bank_record(annual_balance=600)
    await _add_records(db_session_manager, make_profile_record(), bank_record)

    transaction = await _run(db_session_manager, _affect_entry(no_deduction=True), 480)

    assert transaction is None
    assert await _transactions(db_session_manager) == []
    stored = await _get_bank(db_session_manager, bank_record.id)
    assert stored is not None
    assert stored.annual_balance == 600


async def test_zero_deduction_minutes_creates_no_transaction(
    db_session_manager: DbSessionManager,
) -> None:
    bank_record = _pto_bank_record(annual_balance=600)
    await _add_records(db_session_manager, make_profile_record(), bank_record)

    transaction = await _run(db_session_manager, _affect_entry(), 0)

    assert transaction is None
    assert await _transactions(db_session_manager) == []


async def test_remote_work_entry_creates_no_transaction(
    db_session_manager: DbSessionManager,
) -> None:
    bank_record = _pto_bank_record(annual_balance=600)
    await _add_records(db_session_manager, make_profile_record(), bank_record)

    transaction = await _run(
        db_session_manager,
        _affect_entry(no_deduction=True, entry_type=PtoAffectEntryType.REMOTE_WORK),
        480,
    )

    assert transaction is None
    assert await _transactions(db_session_manager) == []


async def test_creates_a_bank_for_the_current_year_when_missing(
    db_session_manager: DbSessionManager,
) -> None:
    await _add_records(
        db_session_manager,
        make_profile_record(work_start_date=date(2020, 6, 15)),
    )

    transaction = await _run(
        db_session_manager,
        _affect_entry(),
        480,
        year=date.today().year,
        service=make_full_deduct_pto_for_entry_service(db_session_manager),
    )

    assert transaction is not None
    assert transaction.value == 480
    stored = await _get_bank(db_session_manager, UUID(transaction.pto_bank_id))
    assert stored is not None
    assert stored.year == date.today().year


async def test_a_past_year_without_a_bank_is_rejected(
    db_session_manager: DbSessionManager,
) -> None:
    await _add_records(db_session_manager, make_profile_record())

    with pytest.raises(AppException) as exc_info:
        await _run(
            db_session_manager,
            _affect_entry(),
            480,
            year=2001,
            service=make_full_deduct_pto_for_entry_service(db_session_manager),
        )

    assert exc_info.value.code == "pto_bank_not_found"
