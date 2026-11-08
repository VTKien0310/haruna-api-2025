import pytest

from app.database import PtoBankRecord
from app.features.pto.entities import PtoBank
from tests.factories.database_records import make_pto_bank_record

ORIGINAL_BALANCE_CASES = [
    pytest.param((120, 45, 30), id="populated"),
    pytest.param((0, 0, 0), id="zero"),
]


@pytest.mark.parametrize("original_balances", ORIGINAL_BALANCE_CASES)
def test_from_db_record_maps_original_balances(
    original_balances: tuple[int, int, int],
) -> None:
    record = make_pto_bank_record(
        original_annual_balance=original_balances[0],
        original_extended_balance=original_balances[1],
        original_seniority_balance=original_balances[2],
    )

    bank = PtoBank.from_db_record(record)

    assert (
        bank.original_annual_balance,
        bank.original_extended_balance,
        bank.original_seniority_balance,
    ) == original_balances


@pytest.mark.parametrize("original_balances", ORIGINAL_BALANCE_CASES)
def test_from_spb_data_maps_original_balances(
    original_balances: tuple[int, int, int],
) -> None:
    data: dict[str, str | int] = {
        "id": "bank-id",
        "owner_id": "owner-id",
        "annual_balance": 600,
        "extended_balance": 50,
        "seniority_balance": 25,
        "original_annual_balance": original_balances[0],
        "original_extended_balance": original_balances[1],
        "original_seniority_balance": original_balances[2],
        "year": 2026,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-02T00:00:00+00:00",
    }

    bank = PtoBank.from_spb_data(data)

    assert (
        bank.original_annual_balance,
        bank.original_extended_balance,
        bank.original_seniority_balance,
    ) == original_balances


def test_original_balances_default_to_zero_and_are_non_nullable() -> None:
    record = make_pto_bank_record()
    table = PtoBankRecord.metadata.tables["pto_banks"]

    assert (
        record.original_annual_balance,
        record.original_extended_balance,
        record.original_seniority_balance,
    ) == (0, 0, 0)
    assert table.c.original_annual_balance.nullable is False
    assert table.c.original_extended_balance.nullable is False
    assert table.c.original_seniority_balance.nullable is False
