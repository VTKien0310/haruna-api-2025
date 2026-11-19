from datetime import date, datetime, timedelta
from uuid import UUID

import pytest
from sqlmodel import SQLModel, select

from app.core import AppException
from app.database import (
    DbSessionManager,
    MissCheckInEntryRecord,
    PtoAffectEntryRecord,
    PtoBankRecord,
    PtoTransactionRecord,
    RemoteWorkEntryRecord,
    TimeOffEntryRecord,
    WorkdayExceptionRecord,
)
from app.features.pto.constants import MINUTES_PER_WORK_DAY
from app.features.pto.data import CreatePtoTransactionWriter
from app.features.pto.entities import PtoAffectEntryType
from app.features.pto.services import GetOrCreatePtoBankService
from app.features.attendance.entities import TimeOffType, WorkdayExceptionTime
from tests.factories.database_records import (
    TEST_PTO_BANK_ID,
    TEST_USER_ID,
    make_profile_record,
    make_pto_bank_record,
)
from tests.support.pto_services import make_get_or_create_pto_bank_service

PREVIOUS_YEAR_BANK_ID = UUID("44444444-4444-4444-8444-444444444444")
OTHER_USER_ID = UUID("55555555-5555-4555-8555-555555555555")
SETTLEMENT_TODAY = date(2027, 1, 15)
PREVIOUS_YEAR_MISSED_DAY = date(2026, 12, 31)


class _SettlementDate(date):
    @classmethod
    def today(cls) -> date:
        return date(2027, 1, 15)


def _pin_settlement_today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.features.pto.services.get_or_create_pto_bank_service.date",
        _SettlementDate,
    )


def _service(db_session_manager: DbSessionManager) -> GetOrCreatePtoBankService:
    return make_get_or_create_pto_bank_service(db_session_manager)


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


def _previous_year_last_day() -> date:
    return date(date.today().year - 1, 12, 31)


def _workday_exception(day: date) -> WorkdayExceptionRecord | None:
    if day.weekday() < 5:
        return None
    return WorkdayExceptionRecord(
        date=day,
        type=0,
        time=WorkdayExceptionTime.FULL_DAY,
        title="Scheduled workday",
    )


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
        make_profile_record(work_start_date=date(current_year, 1, 1)),
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


async def test_settles_previous_year_before_carryover_and_is_idempotent(
    db_session_manager: DbSessionManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _pin_settlement_today(monkeypatch)
    current_year = SETTLEMENT_TODAY.year
    missed_day = PREVIOUS_YEAR_MISSED_DAY
    records: list[SQLModel] = [
        make_profile_record(work_start_date=missed_day),
        make_pto_bank_record(
            id=PREVIOUS_YEAR_BANK_ID,
            year=current_year - 1,
            annual_balance=700,
            extended_balance=120,
            seniority_balance=100,
        ),
    ]
    other_missed_entry = MissCheckInEntryRecord(date=missed_day, penalty=480)
    records.extend(
        [
            other_missed_entry,
            PtoAffectEntryRecord(
                owner_id=OTHER_USER_ID,
                entry_id=other_missed_entry.id,
                entry_type=PtoAffectEntryType.MISS_CHECK_IN.value,
                no_deduction=0,
                title="Other user's missed check-in",
                note="",
            ),
        ]
    )
    exception = _workday_exception(missed_day)
    if exception is not None:
        records.append(exception)
    await _add_records(db_session_manager, *records)

    service = _service(db_session_manager)
    bank = await service.handle(TEST_USER_ID, current_year)
    await service.handle(TEST_USER_ID, current_year)

    assert bank.extended_balance == 440
    assert bank.original_extended_balance == 440
    previous_bank = await _get_bank(db_session_manager, PREVIOUS_YEAR_BANK_ID)
    assert previous_bank is not None
    assert (
        previous_bank.extended_balance,
        previous_bank.seniority_balance,
        previous_bank.annual_balance,
    ) == (0, 0, 440)
    async with db_session_manager.session() as session:
        missed_entries = (await session.exec(select(MissCheckInEntryRecord))).all()
        affect_entries = (
            await session.exec(
                select(PtoAffectEntryRecord).where(
                    PtoAffectEntryRecord.entry_type
                    == PtoAffectEntryType.MISS_CHECK_IN.value
                )
            )
        ).all()
        transactions = (
            await session.exec(
                select(PtoTransactionRecord).where(
                    PtoTransactionRecord.cause == "miss_check_in_entries_create"
                )
            )
        ).all()

    current_affects = [
        affect for affect in affect_entries if affect.owner_id == UUID(TEST_USER_ID)
    ]
    assert len(missed_entries) == len(affect_entries) == 2
    assert len(current_affects) == len(transactions) == 1
    current_entry = next(
        entry for entry in missed_entries if entry.id == current_affects[0].entry_id
    )
    assert current_entry.date == missed_day
    assert current_entry.penalty == 480
    assert current_affects[0].title == f"Missed check-in on {missed_day.isoformat()}"
    assert transactions[0].entry_id == current_affects[0].id
    assert transactions[0].value == 480
    assert transactions[0].exceed_bank_value == 0


async def test_settlement_deducts_only_minutes_uncovered_by_recorded_time_off(
    db_session_manager: DbSessionManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _pin_settlement_today(monkeypatch)
    current_year = SETTLEMENT_TODAY.year
    missed_day = PREVIOUS_YEAR_MISSED_DAY
    time_off = TimeOffEntryRecord(date=missed_day, type=TimeOffType.MORNING)
    records: list[SQLModel] = [
        make_profile_record(work_start_date=missed_day),
        make_pto_bank_record(
            id=PREVIOUS_YEAR_BANK_ID,
            year=current_year - 1,
            annual_balance=1_000,
            seniority_balance=0,
            extended_balance=0,
        ),
        time_off,
        PtoAffectEntryRecord(
            owner_id=UUID(TEST_USER_ID),
            entry_id=time_off.id,
            entry_type=PtoAffectEntryType.TIME_OFF.value,
            no_deduction=0,
            title="Morning time off",
            note="",
        ),
    ]
    exception = _workday_exception(missed_day)
    if exception is not None:
        records.append(exception)
    await _add_records(db_session_manager, *records)

    bank = await _service(db_session_manager).handle(TEST_USER_ID, current_year)

    assert bank.extended_balance == 760
    async with db_session_manager.session() as session:
        missed_entry = (await session.exec(select(MissCheckInEntryRecord))).one()
        transaction = (
            await session.exec(
                select(PtoTransactionRecord).where(
                    PtoTransactionRecord.cause == "miss_check_in_entries_create"
                )
            )
        ).one()

    assert missed_entry.penalty == transaction.value == 240


async def test_settlement_ignores_days_before_go_live(
    db_session_manager: DbSessionManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _pin_settlement_today(monkeypatch)
    current_year = SETTLEMENT_TODAY.year
    before_go_live = date(2026, 11, 17)
    go_live = date(2026, 11, 18)
    records: list[SQLModel] = [
        make_profile_record(work_start_date=date(2026, 11, 16)),
        make_pto_bank_record(
            id=PREVIOUS_YEAR_BANK_ID,
            year=current_year - 1,
            annual_balance=1_000,
            seniority_balance=0,
            extended_balance=0,
        ),
    ]
    day = date(2026, 11, 16)
    while day <= PREVIOUS_YEAR_MISSED_DAY:
        if day.weekday() < 5 and day not in {before_go_live, go_live}:
            remote_work = RemoteWorkEntryRecord(date=day, type=0)
            records.extend(
                [
                    remote_work,
                    PtoAffectEntryRecord(
                        owner_id=UUID(TEST_USER_ID),
                        entry_id=remote_work.id,
                        entry_type=PtoAffectEntryType.REMOTE_WORK.value,
                        no_deduction=0,
                        title="Covered workday",
                        note="",
                    ),
                ]
            )
        day += timedelta(days=1)
    await _add_records(db_session_manager, *records)

    bank = await _service(db_session_manager).handle(TEST_USER_ID, current_year)

    assert bank.extended_balance == 520
    async with db_session_manager.session() as session:
        missed_entries = (await session.exec(select(MissCheckInEntryRecord))).all()
        transaction = (
            await session.exec(
                select(PtoTransactionRecord).where(
                    PtoTransactionRecord.cause == "miss_check_in_entries_create"
                )
            )
        ).one()

    assert [entry.date for entry in missed_entries] == [go_live]
    assert missed_entries[0].penalty == transaction.value == 480


async def test_settlement_is_skipped_without_a_previous_year_bank(
    db_session_manager: DbSessionManager,
) -> None:
    current_year = date.today().year
    missed_day = _previous_year_last_day()
    records: list[SQLModel] = [make_profile_record(work_start_date=missed_day)]
    exception = _workday_exception(missed_day)
    if exception is not None:
        records.append(exception)
    await _add_records(db_session_manager, *records)

    bank = await _service(db_session_manager).handle(TEST_USER_ID, current_year)

    assert bank.extended_balance == 0
    async with db_session_manager.session() as session:
        missed_entries = (await session.exec(select(MissCheckInEntryRecord))).all()
        transactions = (await session.exec(select(PtoTransactionRecord))).all()

    assert missed_entries == []
    assert transactions == []


async def test_settlement_rolls_back_missed_entry_and_balance_when_transaction_fails(
    db_session_manager: DbSessionManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _pin_settlement_today(monkeypatch)
    current_year = SETTLEMENT_TODAY.year
    missed_day = PREVIOUS_YEAR_MISSED_DAY
    records: list[SQLModel] = [
        make_profile_record(work_start_date=missed_day),
        make_pto_bank_record(
            id=PREVIOUS_YEAR_BANK_ID,
            year=current_year - 1,
            annual_balance=700,
            extended_balance=120,
            seniority_balance=100,
        ),
    ]
    exception = _workday_exception(missed_day)
    if exception is not None:
        records.append(exception)
    await _add_records(db_session_manager, *records)

    async def fail_transaction_writer(*args: object, **kwargs: object) -> None:
        raise RuntimeError("transaction writer failed")

    monkeypatch.setattr(CreatePtoTransactionWriter, "handle", fail_transaction_writer)
    with pytest.raises(RuntimeError, match="transaction writer failed"):
        await _service(db_session_manager).handle(TEST_USER_ID, current_year)

    previous_bank = await _get_bank(db_session_manager, PREVIOUS_YEAR_BANK_ID)
    assert previous_bank is not None
    assert (
        previous_bank.extended_balance,
        previous_bank.seniority_balance,
        previous_bank.annual_balance,
    ) == (120, 100, 700)
    async with db_session_manager.session() as session:
        banks = (
            await session.exec(
                select(PtoBankRecord).where(PtoBankRecord.year == current_year)
            )
        ).all()
        missed_entries = (await session.exec(select(MissCheckInEntryRecord))).all()
        affects = (
            await session.exec(
                select(PtoAffectEntryRecord).where(
                    PtoAffectEntryRecord.entry_type
                    == PtoAffectEntryType.MISS_CHECK_IN.value
                )
            )
        ).all()
        transactions = (await session.exec(select(PtoTransactionRecord))).all()

    assert banks == []
    assert missed_entries == []
    assert affects == []
    assert transactions == []


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
            original_seniority_balance=MINUTES_PER_WORK_DAY,
        ),
    )

    bank = await _service(db_session_manager).handle(TEST_USER_ID, date.today().year)

    assert bank.seniority_balance == 2 * MINUTES_PER_WORK_DAY
    assert (
        bank.original_annual_balance,
        bank.original_extended_balance,
        bank.original_seniority_balance,
    ) == (444, 555, 2 * MINUTES_PER_WORK_DAY)
    stored = await _get_bank(db_session_manager, TEST_PTO_BANK_ID)
    assert stored is not None
    assert stored.seniority_balance == 2 * MINUTES_PER_WORK_DAY
    assert (
        stored.original_annual_balance,
        stored.original_extended_balance,
        stored.original_seniority_balance,
    ) == (444, 555, 2 * MINUTES_PER_WORK_DAY)


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
            original_seniority_balance=2 * MINUTES_PER_WORK_DAY,
            updated_at=unchanged_timestamp,
        ),
    )

    bank = await _service(db_session_manager).handle(TEST_USER_ID, date.today().year)

    assert bank.seniority_balance == 2 * MINUTES_PER_WORK_DAY
    assert bank.original_seniority_balance == 2 * MINUTES_PER_WORK_DAY
    stored = await _get_bank(db_session_manager, TEST_PTO_BANK_ID)
    assert stored is not None
    assert stored.seniority_balance == 2 * MINUTES_PER_WORK_DAY
    assert stored.original_seniority_balance == 2 * MINUTES_PER_WORK_DAY
    assert stored.updated_at == unchanged_timestamp


async def test_viewing_current_year_records_seniority_already_ahead_of_original(
    db_session_manager: DbSessionManager,
) -> None:
    await _add_records(
        db_session_manager,
        make_profile_record(work_start_date=_work_start_years_ago(2)),
        make_pto_bank_record(
            id=TEST_PTO_BANK_ID,
            year=date.today().year,
            seniority_balance=2 * MINUTES_PER_WORK_DAY,
            original_seniority_balance=MINUTES_PER_WORK_DAY,
        ),
    )

    bank = await _service(db_session_manager).handle(TEST_USER_ID, date.today().year)

    assert bank.seniority_balance == 2 * MINUTES_PER_WORK_DAY
    assert bank.original_seniority_balance == 2 * MINUTES_PER_WORK_DAY
    stored = await _get_bank(db_session_manager, TEST_PTO_BANK_ID)
    assert stored is not None
    assert stored.seniority_balance == 2 * MINUTES_PER_WORK_DAY
    assert stored.original_seniority_balance == 2 * MINUTES_PER_WORK_DAY


async def test_viewing_current_year_does_not_refill_spent_seniority(
    db_session_manager: DbSessionManager,
) -> None:
    unchanged_timestamp = datetime(2026, 1, 1)
    target = 2 * MINUTES_PER_WORK_DAY
    await _add_records(
        db_session_manager,
        make_profile_record(work_start_date=_work_start_years_ago(2)),
        make_pto_bank_record(
            id=TEST_PTO_BANK_ID,
            year=date.today().year,
            annual_balance=1000,
            seniority_balance=0,
            original_seniority_balance=target,
            updated_at=unchanged_timestamp,
        ),
    )

    bank = await _service(db_session_manager).handle(TEST_USER_ID, date.today().year)

    assert bank.annual_balance == 1000
    assert bank.seniority_balance == 0
    assert bank.original_seniority_balance == target
    stored = await _get_bank(db_session_manager, TEST_PTO_BANK_ID)
    assert stored is not None
    assert stored.annual_balance == 1000
    assert stored.seniority_balance == 0
    assert stored.original_seniority_balance == target
    assert stored.updated_at == unchanged_timestamp


async def test_viewing_current_year_grants_a_new_day_onto_spent_seniority(
    db_session_manager: DbSessionManager,
) -> None:
    await _add_records(
        db_session_manager,
        make_profile_record(work_start_date=_work_start_years_ago(2)),
        make_pto_bank_record(
            id=TEST_PTO_BANK_ID,
            year=date.today().year,
            seniority_balance=0,
            original_seniority_balance=MINUTES_PER_WORK_DAY,
        ),
    )

    bank = await _service(db_session_manager).handle(TEST_USER_ID, date.today().year)

    assert bank.seniority_balance == MINUTES_PER_WORK_DAY
    assert bank.original_seniority_balance == 2 * MINUTES_PER_WORK_DAY
    stored = await _get_bank(db_session_manager, TEST_PTO_BANK_ID)
    assert stored is not None
    assert stored.seniority_balance == MINUTES_PER_WORK_DAY
    assert stored.original_seniority_balance == 2 * MINUTES_PER_WORK_DAY
