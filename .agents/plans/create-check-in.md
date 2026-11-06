# Create check-in

Add `POST /api/attendance/check-ins`. The route records one arrival and the caller's `pto_affect_entries` link to that arrival.

Both writes go through direct PostgreSQL. `CreateCheckInService` opens one `DbSessionManager.transaction()`, passes that `AsyncSession` to every reader and writer, and lets the transaction commit on success. Writers `flush()` and do not `commit()`.

The rules below are settled. Keep them while you implement.

## Rules

- The body is `date` (`YYYY-MM-DD`) and `time` (`HH:MM` or `HH:MM:SS`). Drop seconds and microseconds, and store `HH:MM:00`. Store the value as the company's local clock. Do not convert that clock to another timezone.
- Accept any calendar date and any clock time. A Sunday, a holiday, a remote day, a date outside employment, and a time outside 08:00–17:30 are still stored.
- In the same transaction, insert `check_in_entries`, then `pto_affect_entries`. Set `owner_id` from the authenticated user. Set `entry_id` to the new check-in id. Set `entry_type` to `check_in_entries` (`PtoAffectEntryType.CHECK_IN`). Leave `no_deduction` unset so the stored value is the column default `0`.
- Leave `pto_transactions`, `pto_banks`, and missed-minute calculation unchanged.
- Return `409` with `AppException` code `check_in_already_exists` when this caller already has an affect row of type `check_in_entries` whose check-in is on that date. Leave the stored arrival in place. Another caller's arrival on that date is allowed.
- When the affect insert raises, the transaction rolls back the check-in inserted in that same transaction. Do not catch the failure to delete the check-in. The original error propagates.
- Success returns the stored `CheckInEntry` at `200`. Middleware wraps it as `{"ok": true, "content": ...}`.
- Require a bearer token through `AuthenticatedGuardDep`. The body has no user id.

`check_in_entries` has no owner column. The owner and the date live on different tables, and neither table has a constraint that ties them together. One transaction makes this request's two inserts atomic with each other. Two concurrent transactions for the same caller and date can both pass the existence check and both commit. Do not add a unique index or a database function for that race.

## Model the tables

Add SQLModel table classes in `app/database/models.py`. Use `metadata = model_common_metadata`. Export both from `app/database/__init__.py`.

`CheckInEntryRecord` maps `check_in_entries`:

- `id: UUID`, primary key, `default_factory=uuid4`
- `date: date`
- `time: time`, stored as `time without time zone` through `Column(Time, nullable=False)`

The table has no owner and no timestamps. Do not add them.

`PtoAffectEntryRecord` maps `pto_affect_entries`:

- `id: UUID`, primary key, `default_factory=uuid4`
- `owner_id: UUID`, required. The writer always sends it. Do not copy the hosted `auth.uid()` default into the model, and do not declare the foreign key to `auth.users`. `PtoBankRecord` follows the same shape.
- `entry_id: UUID | None`
- `entry_type: str | None`
- `no_deduction`, a non-null `SmallInteger` with `server_default="0"`. The writer does not pass it. After flush the stored value is `0`. Give the field `default=0` when SQLModel requires a constructor value; the call site still omits the argument.
- `created_at` and `updated_at`, the same `DateTime(timezone=True)` and `_utc_now` defaults as `PtoBankRecord`

Do not add a unique constraint. Do not add `SupabasePort` table methods. Do not change `tests/support/schema.sql` or `SqliteSupabasePort`. These writes use the SQLModel session, and `db_session_manager` creates the tables from this metadata.

## Map the records

Add `CheckInEntry.from_db_record`. It maps `id` with `str`, and copies `date` and `time`. Keep `from_spb_data`.

Add `owner_id: str` to `PtoAffectEntry`, after `id`. Add `from_db_record`. Map `owner_id` and `id` with `str`, `entry_id` with `str` when it is present, `entry_type` with `PtoAffectEntryType` when it is present, and `no_deduction` with `bool(record.no_deduction)`. Read `owner_id` in `from_spb_data` as well. This feature does not call `from_spb_data`.

## Write the arrival

Add these types under `app/features/attendance/data/`. Export each class and each `Dep` alias from `app/features/attendance/data/__init__.py`. Each `handle` is `async` and takes the caller's `AsyncSession` first. Neither class injects `SupabasePort`.

`CreateCheckInEntryWriter.handle(self, db_session: AsyncSession, day: date, arrival: time) -> CheckInEntry` adds a `CheckInEntryRecord` with that date and time, calls `await db_session.flush()`, and returns `CheckInEntry.from_db_record`. The service passes the truncated time. The writer stores that time. It does not generate its own truncation.

`FindCheckInEntryByIdsAndDateReader.handle(self, db_session: AsyncSession, entry_ids: list[str], day: date) -> CheckInEntry | None` returns `None` when `entry_ids` is empty. Otherwise it selects `CheckInEntryRecord` where `id` is in those UUIDs and `date` equals `day`, limited to one row, and returns `CheckInEntry.from_db_record` or `None`.

There is no delete writer. Rollback removes a check-in whose affect insert fails.

## Write the affect row

Add these types under `app/features/pto/data/`. Export them from `app/features/pto/data/__init__.py`. Each `handle` is `async` and takes the caller's `AsyncSession` first.

`FindPtoAffectEntriesByOwnerAndTypeReader.handle(self, db_session: AsyncSession, owner_id: str, entry_type: PtoAffectEntryType) -> list[PtoAffectEntry]` selects `PtoAffectEntryRecord` where `owner_id` is `UUID(owner_id)` and `entry_type` is `entry_type.value`.

`CreatePtoAffectEntryWriter.handle(self, db_session: AsyncSession, owner_id: str, entry_id: str, entry_type: PtoAffectEntryType) -> PtoAffectEntry` adds a `PtoAffectEntryRecord` with `owner_id=UUID(owner_id)`, `entry_id=UUID(entry_id)`, and `entry_type=entry_type.value`. Omit `no_deduction`, `id`, `created_at`, and `updated_at`. `flush()`, then return `PtoAffectEntry.from_db_record`.

## Orchestrate the create

`CreateCheckInService` lives in `app/features/attendance/services/create_check_in_service.py`. Export the class and `CreateCheckInServiceDep` from `app/features/attendance/services/__init__.py`.

Inject `FindPtoAffectEntriesByOwnerAndTypeReader`, `FindCheckInEntryByIdsAndDateReader`, `CreateCheckInEntryWriter`, `CreatePtoAffectEntryWriter`, and `DbSessionManager`. `async def handle(self, user_id: str, day: date, arrival: time) -> CheckInEntry` opens `async with self.__db_session_manager.transaction() as db_session` and, inside that block:

1. Replace `arrival` with `arrival.replace(second=0, microsecond=0)`.
2. Load this caller's affect rows of type `PtoAffectEntryType.CHECK_IN` through the shared session.
3. Keep the `entry_id` values that are not `None`.
4. When a check-in for those ids falls on `day`, raise `AppException` with status `409`, code `check_in_already_exists`, and message `Check-in on '{day}' already exists`. Raise it from inside the transaction. Do not catch it.
5. Insert the check-in through the shared session.
6. Insert the affect row for `user_id` and that check-in id through the same session.
7. Return the `CheckInEntry`.

Do not catch a failure from the affect insert. Leaving the `transaction()` block by exception rolls back the flushed check-in. Do not log the date or the time.

## Expose the route

Add `CreateCheckInRequest` in `app/features/attendance/requests/create_check_in_request.py`. It has two required fields, `date: date` and `time: time`. Export it from `app/features/attendance/requests/__init__.py`.

Add `app/http/attendance_router.py`. Register it in `router_registry` in `app/http/__init__.py`.

Use prefix `/attendance`, tag `attendance`, and `dependencies=[AuthenticatedGuardDep]`. The path is `/check-ins`, so the mounted path is `POST /api/attendance/check-ins`.

The handler is `async`. It takes `CreateCheckInRequest`, `CurrentAuthenticatedUserDep`, and `CreateCheckInServiceDep`. It returns `await create_check_in_service.handle(user.id, request.date, request.time)`.

Follow the description shape in `app/http/pto_router.py`. Summary: `POST /api/attendance/check-ins`. Describe the bearer token, the body, the dropped seconds, and these responses:

- `200`: the stored check-in (`id`, `date`, `time`)
- `401`: `unauthorized` when the bearer token is missing or rejected
- `409`: `check_in_already_exists` when this caller already has an arrival on that date
- `422`: `validation_error` when `date` or `time` is missing or unparseable

Declare the `409` body with `error_response` from `app.core`.

## Prove the behavior

Add `tests/features/attendance/test_create_check_in_service.py`. Construct `CreateCheckInService` with the real readers and writers and pass `db_session_manager` into the service, as `tests/features/pto/test_get_or_create_pto_bank_service.py` does. The readers and writers take the session through `handle()`. Read rows back with a new `db_session_manager.session()` after `handle()` returns or raises.

`owner_id` is a UUID column. Use `TEST_USER_ID` from `tests/factories/database_records.py` and a second UUID string for the other caller. Use fixed dates. `2026-01-04` is a Sunday. `2026-01-05` is a Monday.

Cover these cases:

- `09:00:59` on `2026-01-04` stores `09:00:00`.
- `07:15` on that date stores `07:15:00`.
- The affect row has `owner_id` of the caller, `entry_id` of that check-in, `entry_type` `check_in_entries`, and `no_deduction` `0`.
- A second call for the same caller and date raises `check_in_already_exists` and leaves the first time in place.
- A call for another user id on that same date stores a second check-in.
- No profile row is required. The service has no PTO bank or PTO transaction collaborator. Do not add `PtoTransactionRecord` to assert an empty `pto_transactions` table.

For the affect-insert failure, pass a local writer whose `handle` raises `RuntimeError`. Assert that the error propagates. In a session opened after the exception, `check_in_entries` has no row from that attempt and `pto_affect_entries` has no row from it. Query after the transaction exits, as `tests/database/test_session.py` does for rollback.

Add `tests/http/test_create_check_in.py`. Use the `db_client` fixture so the route receives `db_session_manager`. Register the token with `supabase.auth().register("token-1", user_id=TEST_USER_ID)`. Assert the wrapped body.

Cover these cases:

- A missing token returns `401` and `unauthorized`.
- A valid body returns `200`, `ok` true, and `id`, `date`, and `time` `09:00:00`. The check-in row and the affect row exist on the SQLModel session.
- The same caller and date returns `409` and `check_in_already_exists`.
- A second token registered with another UUID user id can store that same date.
- An unparseable `date` or `time` returns `422` and `validation_error`.

Run the checks from the repository root:

```shell
source .venv/bin/activate
ruff format
ruff check
deactivate
uv run pytest
```
