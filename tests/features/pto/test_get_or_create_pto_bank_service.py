import sqlite3
from datetime import date

import pytest

from app.core import AppException
from app.features.profile.data import FindProfileByUserIdReader
from app.features.pto.constants import MINUTES_PER_WORK_DAY
from app.features.pto.data import (
    CreatePtoBankWriter,
    FindPtoBankByOwnerAndYearReader,
    UpdatePtoBankSeniorityBalanceWriter,
)
from app.features.pto.services import GetOrCreatePtoBankService
from tests.factories.records import insert_pto_bank, insert_profile
from tests.fakes.sqlite_supabase import SqliteSupabasePort


def _service(supabase: SqliteSupabasePort) -> GetOrCreatePtoBankService:
    return GetOrCreatePtoBankService(
        FindPtoBankByOwnerAndYearReader(supabase),
        FindProfileByUserIdReader(supabase),
        CreatePtoBankWriter(supabase),
        UpdatePtoBankSeniorityBalanceWriter(supabase),
    )


def _work_start_years_ago(years: int) -> str:
    today = date.today()
    try:
        start = today.replace(year=today.year - years)
    except ValueError:  # February 29
        start = today.replace(year=today.year - years, day=28)
    return start.isoformat()


def test_creates_current_year_bank_with_default_balances(
    database: sqlite3.Connection, supabase: SqliteSupabasePort
) -> None:
    current_year = date.today().year
    insert_profile(database, user_id="user-1", work_start_date="2020-06-15")

    bank = _service(supabase).handle("user-1", current_year)

    assert bank.owner_id == "user-1"
    assert bank.year == current_year
    assert bank.annual_balance == 13 * MINUTES_PER_WORK_DAY
    assert bank.extended_balance == 0
    assert (
        bank.seniority_balance
        == min(date.today().year - 2020, 8) * MINUTES_PER_WORK_DAY
    )


def test_creates_bank_with_extended_balance_from_last_year(
    database: sqlite3.Connection, supabase: SqliteSupabasePort
) -> None:
    current_year = date.today().year
    insert_profile(database, user_id="user-1")
    insert_pto_bank(
        database,
        owner_id="user-1",
        year=current_year - 1,
        annual_balance=100,
        seniority_balance=50,
    )

    bank = _service(supabase).handle("user-1", current_year)

    assert bank.extended_balance == 150


def test_creates_bank_with_seniority_capped_at_eight_days(
    database: sqlite3.Connection, supabase: SqliteSupabasePort
) -> None:
    insert_profile(
        database, user_id="user-1", work_start_date=_work_start_years_ago(10)
    )

    bank = _service(supabase).handle("user-1", date.today().year)

    assert bank.seniority_balance == 8 * MINUTES_PER_WORK_DAY


def test_creating_past_or_future_year_is_not_allowed(
    database: sqlite3.Connection, supabase: SqliteSupabasePort
) -> None:
    insert_profile(database, user_id="user-1")
    current_year = date.today().year

    for year in (current_year - 1, current_year + 1):
        with pytest.raises(AppException) as exc_info:
            _service(supabase).handle("user-1", year)
        assert exc_info.value.status_code == 404
        assert exc_info.value.code == "pto_bank_not_found"


def test_creation_requires_a_profile(supabase: SqliteSupabasePort) -> None:
    with pytest.raises(AppException) as exc_info:
        _service(supabase).handle("user-1", date.today().year)

    assert exc_info.value.status_code == 404
    assert exc_info.value.code == "profile_not_found"


def test_viewing_past_year_returns_the_record_unchanged(
    database: sqlite3.Connection, supabase: SqliteSupabasePort
) -> None:
    insert_profile(database, user_id="user-1", work_start_date="2010-01-01")
    insert_pto_bank(
        database,
        id="bank-past",
        owner_id="user-1",
        year=date.today().year - 1,
        seniority_balance=0,
        updated_at="2026-01-01T00:00:00",
    )

    bank = _service(supabase).handle("user-1", date.today().year - 1)

    assert bank.id == "bank-past"
    assert bank.seniority_balance == 0
    stored = (
        supabase.table_pto_bank().select().eq("id", "bank-past").single().execute().data
    )
    assert stored["seniority_balance"] == 0
    assert stored["updated_at"] == "2026-01-01T00:00:00"


def test_viewing_current_year_accrues_seniority_and_persists(
    database: sqlite3.Connection, supabase: SqliteSupabasePort
) -> None:
    insert_profile(database, user_id="user-1", work_start_date=_work_start_years_ago(2))
    insert_pto_bank(
        database,
        id="bank-1",
        owner_id="user-1",
        year=date.today().year,
        seniority_balance=MINUTES_PER_WORK_DAY,
    )

    bank = _service(supabase).handle("user-1", date.today().year)

    assert bank.seniority_balance == 2 * MINUTES_PER_WORK_DAY
    stored = (
        supabase.table_pto_bank().select().eq("id", "bank-1").single().execute().data
    )
    assert stored["seniority_balance"] == 2 * MINUTES_PER_WORK_DAY


def test_viewing_current_year_does_not_accrue_before_the_anniversary(
    database: sqlite3.Connection, supabase: SqliteSupabasePort
) -> None:
    insert_profile(database, user_id="user-1", work_start_date=_work_start_years_ago(2))
    insert_pto_bank(
        database,
        id="bank-1",
        owner_id="user-1",
        year=date.today().year,
        seniority_balance=2 * MINUTES_PER_WORK_DAY,
        updated_at="2026-01-01T00:00:00",
    )

    bank = _service(supabase).handle("user-1", date.today().year)

    assert bank.seniority_balance == 2 * MINUTES_PER_WORK_DAY
    stored = (
        supabase.table_pto_bank().select().eq("id", "bank-1").single().execute().data
    )
    assert stored["updated_at"] == "2026-01-01T00:00:00"
