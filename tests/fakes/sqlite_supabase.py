import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace

from tests.support.database import quote_identifier
from tests.support.isolation import unexpected_interaction


@dataclass
class AuthUser:
    id: str
    aud: str
    created_at: datetime


class AuthFake:
    def __init__(self) -> None:
        self._users: dict[str, AuthUser | None] = {}

    def register(self, token: str, user_id: str = "user-1") -> AuthUser:
        user = AuthUser(
            id=user_id,
            aud="authenticated",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        self._users[token] = user
        return user

    def reject(self, token: str) -> None:
        self._users[token] = None

    def get_user(self, token: str) -> SimpleNamespace | None:
        if token not in self._users:
            unexpected_interaction("Supabase auth get_user")
        user = self._users[token]
        if user is None:
            return None
        return SimpleNamespace(user=user)


class StorageBucket:
    def __init__(self, bucket: str) -> None:
        self._bucket = bucket
        self._files: dict[str, bytes] = {}

    def upload(
        self, path: str, file: bytes, file_options: dict[str, str] | None = None
    ) -> None:
        self._files[path] = file

    def download(self, path: str) -> bytes:
        if path not in self._files:
            unexpected_interaction(f"storage download of missing object {path}")
        return self._files[path]

    def list(
        self, path: str, options: dict[str, object] | None = None
    ) -> list[dict[str, str]]:
        options = options or {}
        search = options.get("search")
        prefix = path.strip("/")
        names = []
        for key in self._files:
            if key == prefix:
                name = key
            elif key.startswith(f"{prefix}/"):
                name = key[len(prefix) + 1 :]
            else:
                continue
            if "/" in name:
                continue
            if isinstance(search, str) and search not in name:
                continue
            names.append(name)

        sort_by = options.get("sortBy")
        reverse = False
        if isinstance(sort_by, dict) and sort_by.get("order") == "desc":
            reverse = True
        names.sort(reverse=reverse)

        offset = options.get("offset")
        limit = options.get("limit")
        start = offset if isinstance(offset, int) else 0
        if isinstance(limit, int):
            names = names[start : start + limit]
        elif start:
            names = names[start:]
        return [{"name": name} for name in names]

    def create_signed_url(self, path: str, expires_in: int) -> dict[str, str]:
        if path not in self._files:
            unexpected_interaction(f"storage signed URL for missing object {path}")
        return {
            "signedUrl": (
                f"https://storage.invalid/{self._bucket}/{path}?expires={expires_in}"
            )
        }


class QueryResult:
    def __init__(
        self, data: list[dict[str, object]] | dict[str, object] | None
    ) -> None:
        self.data = data


class Query:
    def __init__(self, connection: sqlite3.Connection, table: str) -> None:
        self._connection = connection
        self._table = table
        self._operation = "select"
        self._columns = "*"
        self._filters: list[tuple[str, tuple[object, ...]]] = []
        self._order_column: str | None = None
        self._order_desc = False
        self._single = False
        self._rows: list[dict[str, object]] = []

    def select(self, columns: str = "*") -> "Query":
        self._operation = "select"
        self._columns = columns
        return self

    def eq(self, column: str, value: object) -> "Query":
        self._filters.append((f"{quote_identifier(column)} = ?", (value,)))
        return self

    def order(self, column: str, desc: bool = False) -> "Query":
        self._order_column = column
        self._order_desc = desc
        return self

    def in_(self, column: str, values: list[object]) -> "Query":
        if not values:
            self._filters.append(("0", ()))
            return self
        placeholders = ", ".join("?" for _ in values)
        self._filters.append(
            (f"{quote_identifier(column)} IN ({placeholders})", tuple(values))
        )
        return self

    def insert(self, row: dict[str, object] | list[dict[str, object]]) -> "Query":
        self._operation = "insert"
        self._rows = row if isinstance(row, list) else [row]
        return self

    def delete(self) -> "Query":
        self._operation = "delete"
        return self

    def single(self) -> "Query":
        self._single = True
        return self

    def execute(self) -> QueryResult:
        if self._operation == "insert":
            return self._execute_insert()
        if self._operation == "delete":
            return self._execute_delete()
        return self._execute_select()

    def _execute_select(self) -> QueryResult:
        column_sql = "*"
        if self._columns != "*":
            column_sql = ", ".join(
                quote_identifier(column.strip()) for column in self._columns.split(",")
            )
        where_sql, params = self._where()
        order_sql = ""
        if self._order_column is not None:
            direction = "DESC" if self._order_desc else "ASC"
            order_sql = f" ORDER BY {quote_identifier(self._order_column)} {direction}"
        rows = self._connection.execute(
            f"SELECT {column_sql} FROM {quote_identifier(self._table)}{where_sql}{order_sql}",
            params,
        ).fetchall()
        records = [_row_dict(row) for row in rows]
        if self._single:
            if not records:
                return QueryResult(None)
            if len(records) > 1:
                raise RuntimeError(f"{self._table} single() matched more than one row")
            return QueryResult(records[0])
        return QueryResult(records)

    def _execute_insert(self) -> QueryResult:
        inserted: list[dict[str, object]] = []
        for row in self._rows:
            columns = list(row)
            cursor = self._connection.execute(
                (
                    f"INSERT INTO {quote_identifier(self._table)} "
                    f"({', '.join(quote_identifier(column) for column in columns)}) "
                    f"VALUES ({', '.join('?' for _ in columns)})"
                ),
                [row[column] for column in columns],
            )
            fetched = self._connection.execute(
                f"SELECT * FROM {quote_identifier(self._table)} WHERE rowid = ?",
                (cursor.lastrowid,),
            ).fetchone()
            if fetched is None:
                raise RuntimeError(f"Insert into {self._table} did not return a row")
            inserted.append(_row_dict(fetched))
        self._connection.commit()
        return QueryResult(inserted)

    def _execute_delete(self) -> QueryResult:
        where_sql, params = self._where()
        self._connection.execute(
            f"DELETE FROM {quote_identifier(self._table)}{where_sql}",
            params,
        )
        self._connection.commit()
        return QueryResult([])

    def _where(self) -> tuple[str, tuple[object, ...]]:
        if not self._filters:
            return "", ()
        clauses = [clause for clause, _params in self._filters]
        params = tuple(param for _clause, values in self._filters for param in values)
        return " WHERE " + " AND ".join(clauses), params


def _row_dict(row: sqlite3.Row) -> dict[str, object]:
    return {key: row[key] for key in row.keys()}


class SqliteSupabasePort:
    """Supabase stand-in: table rows in SQLite, auth and storage in memory."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self._auth = AuthFake()
        self._storage = {
            "medias": StorageBucket("medias"),
            "resized": StorageBucket("resized"),
            "thumbnails": StorageBucket("thumbnails"),
        }

    def table_media(self) -> Query:
        return Query(self._connection, "medias")

    def table_translation_history(self) -> Query:
        return Query(self._connection, "translation_histories")

    def storage_media(self) -> StorageBucket:
        return self._storage["medias"]

    def storage_resized(self) -> StorageBucket:
        return self._storage["resized"]

    def storage_thumbnails(self) -> StorageBucket:
        return self._storage["thumbnails"]

    def auth(self) -> AuthFake:
        return self._auth
