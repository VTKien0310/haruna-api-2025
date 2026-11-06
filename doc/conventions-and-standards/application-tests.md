# Application tests

Pytest runs the API in memory. No environment file, credential, Docker container, Supabase project, or development server is needed or permitted. Each test gets fresh in-memory SQLite databases for the Supabase table double and direct SQLModel access as needed. Auth, object storage, and AI responses stay in memory.

Commands:

```shell
uv run pytest
uv run pytest tests/features/media
uv run pytest --cov=app --cov-report=term-missing --cov-report=html --cov-report=lcov
```

Coverage includes untested application code and has no percentage gate. HTML and LCOV reports are written to `coverage/` and are Git-ignored.

## Structure

Tests mirror the application under `tests/features/`, `tests/http/`, `tests/database/`, `tests/ports/`, and `tests/architecture/`. `tests/conftest.py` forces `ENVIRONMENT=testing`, dummy Supabase, AI, and database settings, a network block, and a block on constructing the real Supabase client. `tests/support/` holds the Supabase table-double schema, its database connection, and the isolation checks. `tests/factories/records.py` inserts deterministic table-double rows, while `tests/factories/database_records.py` builds deterministic SQLModel records. `tests/fakes/` holds the SQLite-backed Supabase stand-in and the AI stand-in.

- Name files `test_*.py`. Assert observable success and failure: returned entities, row counts, status codes, and the wrapped `{"ok": ...}` body. Do not test private methods.
- Pass `supabase` into a Supabase-backed reader, writer, or service constructor. HTTP tests use the `client` fixture, which overrides `SupabasePort` and the AI port factory with the same fakes.
- Direct-database services receive `db_session_manager`, and their readers and writers receive its `AsyncSession` through `handle()`. HTTP tests for these services use `db_client`, which also overrides `get_db_session_manager`.
- Build table-double rows with the `insert_*` helpers and SQLModel rows with the `make_*_record` helpers. Pass keyword overrides for any column that matters to the assertion.
- Register a bearer token with `supabase.auth().register(token)` before a protected request. `reject(token)` configures an unknown user. A token that was neither registered nor rejected fails the test.
- Upload storage bytes with `supabase.storage_media()`, `storage_resized()`, or `storage_thumbnails()` before the code downloads them. Queue an AI payload with `ai.queue_chat_completion(...)` before the code calls the model.
- The table double supports the query chain the application uses today: `select`, `eq`, `order` (ascending by default), `in_`, `insert`, `update`, `delete`, `single`, and `execute().data`. `single()` yields `data=None` when no row matches.

## Database

`tests/support/schema.sql` creates the tables behind the feature entities: media, translation history, profiles, PTO, and attendance. `id` and timestamps default so a writer that omits them can still insert. `pto_transactions` references `pto_banks` and `pto_affect_entries`.

The table-double database URI is always `file:{name}?mode=memory&cache=shared`. The opener refuses a filesystem path. Closing the connection drops the database, so the next test starts empty.

The `db_session_manager` fixture uses `sqlite+aiosqlite:///:memory:` with `StaticPool` and creates tables from SQLModel metadata in that isolated database only. Its transaction tests verify both commit and rollback. Closing the fixture disposes the engine; no test uses the configured PostgreSQL host or credentials.

These tests do not validate hosted migrations, PostgreSQL-specific behavior, row-level security, or real object storage.

## Network safety

- Real Supabase client construction raises, and the violation is still reported if application code catches the error.
- Outbound sockets and name resolution raise the same way, including any attempted direct PostgreSQL connection.
- Unconfigured auth, storage, and AI calls fail the test even when application code catches them.
- Only the isolation self-tests may consume an expected guard violation, and they must assert that violation before the test ends.
- Never point tests at a development or production environment file, credential, or database.
