# Create check-in

Add `POST /api/attendance/check-ins`. The route records one arrival and the caller's `pto_affect_entries` link to that arrival.

The rules below are settled. Keep them while you implement.

## Rules

- The body is `date` (`YYYY-MM-DD`) and `time` (`HH:MM` or `HH:MM:SS`). Drop seconds and microseconds, and store `HH:MM:00`. Store the value as the company's local clock. Do not convert that clock to another timezone.
- Accept any calendar date and any clock time. A Sunday, a holiday, a remote day, a date outside employment, and a time outside 08:00–17:30 are still stored.
- Insert `check_in_entries`, then `pto_affect_entries`. Set `owner_id` from the authenticated user. Set `entry_id` to the new check-in id. Set `entry_type` to `check_in_entries` (`PtoAffectEntryType.CHECK_IN`). Leave `no_deduction` unset so the database default `0` applies.
- Leave `pto_transactions`, `pto_banks`, and missed-minute calculation unchanged.
- Return `409` with `AppException` code `check_in_already_exists` when this caller already has an affect row of type `check_in_entries` whose check-in is on that date. Leave the stored arrival in place. Another caller's arrival on that date is allowed.
- When the affect insert fails, delete the check-in this request inserted, then re-raise that failure.
- Success returns the stored `CheckInEntry` at `200`. Middleware wraps it as `{"ok": true, "content": ...}`.
- Require a bearer token through `AuthenticatedGuardDep`. The body has no user id.

`check_in_entries` has no owner column. The owner and the date live on different tables, and neither table has a constraint that ties them together. Two concurrent requests for the same caller and date can both pass the existence check. Do not add a unique index or a database function for that race.

If that delete also fails, the delete error propagates and the check-in row can remain.

## Wire the tables

Add `table_check_in_entry()` and `table_pto_affect_entry()` on `SupabasePort` in `app/ports/supabase/spb.py`. Point them at `check_in_entries` and `pto_affect_entries`. Add the same two methods on `SqliteSupabasePort` in `tests/fakes/sqlite_supabase.py`.

## Match the test schema

`doc/design-and-decision/erd.dbml` already has `pto_affect_entries.owner_id`. `tests/support/schema.sql` does not.

Add `owner_id TEXT NOT NULL` to `pto_affect_entries` in `tests/support/schema.sql`. Give the column no SQLite default. The hosted default `auth.uid()` stays in Postgres. The writer always sends `owner_id`.

Add `owner_id: str` to `PtoAffectEntry` and read it in `from_spb_data`. Set `"owner_id": "user-1"` in `insert_pto_affect_entry` so `test_schema_accepts_one_row_per_table` still inserts.

## Write the arrival

Add these types under `app/features/attendance/`. Export each class and each `Dep` alias from that package's `__init__.py`.

`CreateCheckInRequest` in `requests/create_check_in_request.py` has two required fields, `date: date` and `time: time`.

`CreateCheckInEntryWriter.handle(self, day: date, arrival: time) -> CheckInEntry` inserts `date` and `time` as ISO strings and returns `CheckInEntry.from_spb_data` on the inserted row. The service passes the truncated time. The writer stores that time.

`DeleteCheckInEntryWriter.handle(self, check_in_id: str) -> None` deletes the row with that id.

`FindCheckInEntryByIdsAndDateReader.handle(self, entry_ids: list[str], day: date) -> CheckInEntry | None` returns `None` when `entry_ids` is empty. Otherwise it selects `check_in_entries` with `id` in those ids and `date` equal to `day.isoformat()`, and returns the first row.

## Write the affect row

Add these types under `app/features/pto/data/`. Export them from `app/features/pto/data/__init__.py`.

`FindPtoAffectEntriesByOwnerAndTypeReader.handle(self, owner_id: str, entry_type: PtoAffectEntryType) -> list[PtoAffectEntry]` filters with `eq("owner_id", owner_id)` and `eq("entry_type", entry_type.value)`.

`CreatePtoAffectEntryWriter.handle(self, owner_id: str, entry_id: str, entry_type: PtoAffectEntryType) -> PtoAffectEntry` inserts `owner_id`, `entry_id`, and `entry_type`. Omit `no_deduction`, `id`, `created_at`, and `updated_at`.

## Orchestrate the create

`CreateCheckInService` lives in `app/features/attendance/services/create_check_in_service.py`. Inject `FindPtoAffectEntriesByOwnerAndTypeReader`, `FindCheckInEntryByIdsAndDateReader`, `CreateCheckInEntryWriter`, `CreatePtoAffectEntryWriter`, and `DeleteCheckInEntryWriter`. `handle(self, user_id: str, day: date, arrival: time) -> CheckInEntry` does this:

1. Replace `arrival` with `arrival.replace(second=0, microsecond=0)`.
2. Load this caller's affect rows of type `PtoAffectEntryType.CHECK_IN`.
3. Keep the `entry_id` values that are not `None`.
4. When a check-in for those ids falls on `day`, raise `AppException` with status `409`, code `check_in_already_exists`, and message `Check-in on '{day}' already exists`.
5. Insert the check-in.
6. Insert the affect row for `user_id` and that check-in id.
7. When the affect insert raises, delete that check-in id, then re-raise the original error.
8. Return the `CheckInEntry`.

Do not log the date or the time.

## Expose the route

Add `app/http/attendance_router.py`. Register it in `router_registry` in `app/http/__init__.py`.

Use prefix `/attendance`, tag `attendance`, and `dependencies=[AuthenticatedGuardDep]`. The path is `/check-ins`, so the mounted path is `POST /api/attendance/check-ins`.

The handler takes `CreateCheckInRequest`, `CurrentAuthenticatedUserDep`, and `CreateCheckInServiceDep`. It returns `create_check_in_service.handle(user.id, request.date, request.time)`.

Follow the description shape in `app/http/pto_router.py`. Summary: `POST /api/attendance/check-ins`. Describe the bearer token, the body, the dropped seconds, and these responses:

- `200`: the stored check-in (`id`, `date`, `time`)
- `401`: `unauthorized` when the bearer token is missing or rejected
- `409`: `check_in_already_exists` when this caller already has an arrival on that date
- `422`: `validation_error` when `date` or `time` is missing or unparseable

Declare the `409` body with `error_response` from `app.core`.

## Prove the behavior

Add `tests/features/attendance/test_create_check_in_service.py`. Construct `CreateCheckInService` with the real readers and writers, and pass `supabase` into them, as `tests/features/pto/test_get_or_create_pto_bank_service.py` does. Use fixed dates. `2026-01-04` is a Sunday. `2026-01-05` is a Monday.

Cover these cases:

- `09:00:59` on `2026-01-04` stores `09:00:00`.
- `07:15` on that date stores `07:15:00`.
- The affect row has `owner_id` of the caller, `entry_id` of that check-in, `entry_type` `check_in_entries`, and `no_deduction` `0`.
- A second call for the same caller and date raises `check_in_already_exists` and leaves the first time in place.
- A call for another `user_id` on that same date stores a second check-in.
- No profile row is required. `pto_transactions` stays empty.

For the affect-insert failure, pass a local writer whose `handle` raises `RuntimeError`. Assert that the error propagates and that `check_in_entries` has no row for that insert.

Add `tests/http/test_create_check_in.py`. Register the token with `supabase.auth().register`. The default user id is `user-1`. Assert the wrapped body.

Cover these cases:

- A missing token returns `401` and `unauthorized`.
- A valid body returns `200`, `ok` true, and `id`, `date`, and `time` `09:00:00`. The check-in row and the affect row exist. `pto_transactions` is empty.
- The same caller and date returns `409` and `check_in_already_exists`.
- A second token registered as `user-2` can store that same date.
- An unparseable `date` or `time` returns `422` and `validation_error`.

Run the checks from the repository root:

```shell
source .venv/bin/activate
ruff format
ruff check
deactivate
uv run pytest
```
