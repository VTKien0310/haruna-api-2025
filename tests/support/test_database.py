import sqlite3

import pytest

from tests.factories.records import (
    insert_check_in_entry,
    insert_leave_work_entry,
    insert_media,
    insert_profile,
    insert_pto_affect_entry,
    insert_pto_bank,
    insert_pto_transaction,
    insert_remote_work_entry,
    insert_time_off_entry,
    insert_translation_history,
    insert_work_time_entry,
    insert_workday_exception,
)
from tests.support.database import open_sqlite, quote_identifier


def test_database_fixture_refuses_a_filesystem_path() -> None:
    with pytest.raises(RuntimeError, match="filesystem"):
        open_sqlite("file:/tmp/haruna.sqlite")


def test_each_test_gets_an_empty_database(database: sqlite3.Connection) -> None:
    count = database.execute("SELECT COUNT(*) AS total FROM medias").fetchone()
    assert count is not None
    assert count["total"] == 0


def test_schema_accepts_one_row_per_table(database: sqlite3.Connection) -> None:
    insert_media(database)
    insert_translation_history(database)
    insert_profile(database)
    insert_pto_bank(database)
    insert_pto_affect_entry(database)
    insert_pto_transaction(database)
    insert_check_in_entry(database)
    insert_leave_work_entry(database)
    insert_remote_work_entry(database)
    insert_time_off_entry(database)
    insert_work_time_entry(database)
    insert_workday_exception(database)

    tables = [
        "medias",
        "translation_histories",
        "profiles",
        "pto_banks",
        "pto_affect_entries",
        "pto_transactions",
        "check_in_entries",
        "leave_work_entries",
        "remote_work_entries",
        "time_off_entries",
        "work_time_entries",
        "workday_exceptions",
    ]
    for table in tables:
        count = database.execute(
            f"SELECT COUNT(*) AS total FROM {quote_identifier(table)}"
        ).fetchone()
        assert count is not None
        assert count["total"] == 1


def test_pto_transaction_requires_a_bank_and_affect_entry(
    database: sqlite3.Connection,
) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        insert_pto_transaction(
            database, id="tx-missing", pto_bank_id="missing", entry_id="missing"
        )
