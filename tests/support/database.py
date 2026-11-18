import re
import sqlite3
from pathlib import Path
from uuid import uuid4

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SCHEMA = Path(__file__).with_name("schema.sql")


def quote_identifier(identifier: str) -> str:
    if not _IDENTIFIER.fullmatch(identifier):
        raise ValueError(f"Invalid SQL identifier: {identifier}")
    return f'"{identifier}"'


def open_sqlite(uri: str) -> sqlite3.Connection:
    if (
        not uri.startswith("file:")
        or "mode=memory" not in uri
        or "/" in uri
        or "\\" in uri
        or ".sqlite" in uri
    ):
        raise RuntimeError("Refusing filesystem SQLite database")

    connection = sqlite3.connect(uri, uri=True, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(_SCHEMA.read_text(encoding="utf-8"))
    return connection


def connect_test_database() -> sqlite3.Connection:
    name = f"mem{uuid4().hex}"
    return open_sqlite(f"file:{name}?mode=memory&cache=shared")
