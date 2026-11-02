# Application tests

Pytest runs the API in memory. No environment file, credential, Docker container, Supabase project, or development server is needed or permitted. Each test gets a new in-memory SQLite database. Auth, object storage, and AI responses stay in memory.

Commands:

```shell
uv run pytest
uv run pytest tests/features/media
uv run pytest --cov=app --cov-report=term-missing --cov-report=html --cov-report=lcov
```

Coverage includes untested application code and has no percentage gate. HTML and LCOV reports are written to `coverage/` and are Git-ignored.

## Structure

Tests mirror the application under `tests/features/`, `tests/http/`, `tests/ports/`, and `tests/architecture/`. `tests/conftest.py` forces `ENVIRONMENT=testing`, dummy Supabase and AI settings, a network block, and a block on constructing the real Supabase client. `tests/support/` holds the schema, the database connection, and the isolation checks. `tests/factories/records.py` inserts deterministic rows. `tests/fakes/` holds the SQLite-backed Supabase stand-in and the AI stand-in.

- Name files `test_*.py`. Assert observable success and failure: returned entities, row counts, status codes, and the wrapped `{"ok": ...}` body. Do not test private methods.
- Pass `supabase` into a reader, writer, or service constructor. HTTP tests use the `client` fixture, which overrides `SupabasePort` and the AI port factory with the same fakes.
- Build rows with the `insert_*` helpers. Pass keyword overrides for any column that matters to the assertion.
- Register a bearer token with `supabase.auth().register(token)` before a protected request. `reject(token)` configures an unknown user. A token that was neither registered nor rejected fails the test.
- Upload storage bytes with `supabase.storage_media()`, `storage_resized()`, or `storage_thumbnails()` before the code downloads them. Queue an AI payload with `ai.queue_chat_completion(...)` before the code calls the model.
- The table double supports the query chain the application uses today: `select`, `eq`, `order` (ascending by default), `in_`, `insert`, `delete`, `single`, and `execute().data`. `single()` yields `data=None` when no row matches.

## Database

`tests/support/schema.sql` creates the tables behind the feature entities: media, translation history, profiles, PTO, and attendance. `id` and timestamps default so a writer that omits them can still insert. `pto_transactions` references `pto_banks` and `pto_affect_entries`.

The database URI is always `file:{name}?mode=memory&cache=shared`. The opener refuses a filesystem path. Closing the connection drops the database, so the next test starts empty.

These tests do not validate hosted migrations, row-level security, or real object storage.

## Network safety

- Real Supabase client construction raises, and the violation is still reported if application code catches the error.
- Outbound sockets and name resolution raise the same way.
- Unconfigured auth, storage, and AI calls fail the test even when application code catches them.
- Only the isolation self-tests may consume an expected guard violation, and they must assert that violation before the test ends.
- Never point tests at a development or production environment file, credential, or database.
