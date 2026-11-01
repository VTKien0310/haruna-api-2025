import sqlite3

from tests.support.database import quote_identifier


def insert_row(
    connection: sqlite3.Connection, table: str, row: dict[str, object]
) -> dict[str, object]:
    columns = list(row)
    connection.execute(
        (
            f"INSERT INTO {quote_identifier(table)} "
            f"({', '.join(quote_identifier(column) for column in columns)}) "
            f"VALUES ({', '.join('?' for _ in columns)})"
        ),
        [row[column] for column in columns],
    )
    connection.commit()
    return row


def insert_media(
    connection: sqlite3.Connection, **overrides: object
) -> dict[str, object]:
    row: dict[str, object] = {
        "id": "media-1",
        "name": "photo.jpg",
        "type": 0,
        "storage_path": "media-1/photo.jpg",
        "thumbnail_path": None,
        "mime": "image/jpeg",
        "size": 4,
        "uploader_id": "user-1",
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
    }
    row.update(overrides)
    return insert_row(connection, "medias", row)


def insert_translation_history(
    connection: sqlite3.Connection, **overrides: object
) -> dict[str, object]:
    row: dict[str, object] = {
        "id": "history-1",
        "owner_id": "user-1",
        "source_language": "en",
        "target_language": "ja",
        "source_text": "hello",
        "translation": "こんにちは",
        "created_at": "2026-01-01T00:00:00",
    }
    row.update(overrides)
    return insert_row(connection, "translation_histories", row)


def insert_profile(
    connection: sqlite3.Connection, **overrides: object
) -> dict[str, object]:
    row: dict[str, object] = {
        "id": "profile-1",
        "user_id": "user-1",
        "name": "Haruna",
        "birth_date": "2000-01-01",
        "work_start_date": "2024-04-01",
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
    }
    row.update(overrides)
    return insert_row(connection, "profiles", row)


def insert_pto_bank(
    connection: sqlite3.Connection, **overrides: object
) -> dict[str, object]:
    row: dict[str, object] = {
        "id": "pto-bank-1",
        "owner_id": "user-1",
        "annual_balance": 10,
        "extended_balance": 0,
        "seniority_balance": 1,
        "year": 2026,
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
    }
    row.update(overrides)
    return insert_row(connection, "pto_banks", row)


def insert_pto_affect_entry(
    connection: sqlite3.Connection, **overrides: object
) -> dict[str, object]:
    row: dict[str, object] = {
        "id": "pto-affect-1",
        "entry_id": "check-in-1",
        "entry_type": "check_in_entries",
        "no_deduction": 0,
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
    }
    row.update(overrides)
    return insert_row(connection, "pto_affect_entries", row)


def insert_pto_transaction(
    connection: sqlite3.Connection, **overrides: object
) -> dict[str, object]:
    row: dict[str, object] = {
        "id": "pto-transaction-1",
        "pto_bank_id": "pto-bank-1",
        "entry_id": "pto-affect-1",
        "cause": "annual",
        "value": -1,
        "created_at": "2026-01-01T00:00:00",
    }
    row.update(overrides)
    return insert_row(connection, "pto_transactions", row)


def insert_check_in_entry(
    connection: sqlite3.Connection, **overrides: object
) -> dict[str, object]:
    row: dict[str, object] = {
        "id": "check-in-1",
        "date": "2026-01-05",
        "time": "09:00:00",
    }
    row.update(overrides)
    return insert_row(connection, "check_in_entries", row)


def insert_leave_work_entry(
    connection: sqlite3.Connection, **overrides: object
) -> dict[str, object]:
    row: dict[str, object] = {
        "id": "leave-work-1",
        "date": "2026-01-05",
        "start": "15:00:00",
        "end": "18:00:00",
    }
    row.update(overrides)
    return insert_row(connection, "leave_work_entries", row)


def insert_remote_work_entry(
    connection: sqlite3.Connection, **overrides: object
) -> dict[str, object]:
    row: dict[str, object] = {
        "id": "remote-work-1",
        "date": "2026-01-06",
        "type": 0,
    }
    row.update(overrides)
    return insert_row(connection, "remote_work_entries", row)


def insert_time_off_entry(
    connection: sqlite3.Connection, **overrides: object
) -> dict[str, object]:
    row: dict[str, object] = {
        "id": "time-off-1",
        "date": "2026-01-07",
        "type": 0,
    }
    row.update(overrides)
    return insert_row(connection, "time_off_entries", row)


def insert_work_time_entry(
    connection: sqlite3.Connection, **overrides: object
) -> dict[str, object]:
    row: dict[str, object] = {
        "id": "work-time-1",
        "date": "2026-01-08",
        "type": 0,
    }
    row.update(overrides)
    return insert_row(connection, "work_time_entries", row)


def insert_workday_exception(
    connection: sqlite3.Connection, **overrides: object
) -> dict[str, object]:
    row: dict[str, object] = {
        "id": "workday-exception-1",
        "type": 1,
        "date": "2026-01-01",
        "time": 0,
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:00",
    }
    row.update(overrides)
    return insert_row(connection, "workday_exceptions", row)
