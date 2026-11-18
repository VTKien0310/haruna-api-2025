from datetime import date
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from app.database import (
    DbSessionManager,
    PtoAffectEntryRecord,
    PtoBankRecord,
    PtoTransactionRecord,
    WorkTimeEntryRecord,
)
from tests.factories.database_records import (
    TEST_PTO_BANK_ID,
    TEST_USER_ID,
    make_profile_record,
    make_pto_bank_record,
)
from tests.fakes.sqlite_supabase import SqliteSupabasePort

HEADERS = {"Authorization": "Bearer update-token"}
DAY = date(date.today().year, 6, 15).isoformat()
CASES = [
    (
        "check-ins",
        {"date": DAY, "time": "09:30"},
        {"time": "10:00:59"},
        "time",
        "10:00:00",
    ),
    ("time-offs", {"start_date": DAY, "type": 0}, {"type": 1}, "type", 1),
    ("remote-works", {"date": DAY, "type": 0}, {"type": 2}, "type", 2),
    (
        "work-times",
        {"date": DAY, "time": 0, "type": 0, "duration": 60},
        {"duration": 90},
        "duration",
        90,
    ),
    (
        "leave-works",
        {"date": DAY, "start": "09:00", "end": "10:00"},
        {"end": "09:30:59"},
        "end",
        "09:30:00",
    ),
]


async def seed(
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
    *,
    annual: int = 5000,
    extended: int = 20,
    seniority: int = 40,
) -> None:
    supabase.auth().register("update-token", user_id=TEST_USER_ID)
    async with db_session_manager.transaction() as session:
        session.add(make_profile_record(work_start_date=date.today()))
        session.add(
            make_pto_bank_record(
                year=date.today().year,
                annual_balance=annual,
                extended_balance=extended,
                seniority_balance=seniority,
                original_annual_balance=annual,
                original_extended_balance=extended,
                original_seniority_balance=seniority,
            )
        )


def create(client: TestClient, route: str, body: dict[str, str | int | None]) -> str:
    response = client.post(f"/api/attendance/{route}", json=body, headers=HEADERS)
    assert response.status_code == 200, response.text
    content = response.json()["content"]
    return content[0]["id"] if isinstance(content, list) else content["id"]


@pytest.mark.parametrize("route,body,patch,field,expected", CASES)
async def test_patch_each_type(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
    route: str,
    body: dict[str, str | int | None],
    patch: dict[str, str | int | None],
    field: str,
    expected: str | int,
) -> None:
    await seed(db_session_manager, supabase)
    entry_id = create(db_client, route, body | {"note": "preserve"})
    response = db_client.patch(
        f"/api/attendance/{route}/{entry_id}", json=patch, headers=HEADERS
    )
    assert response.status_code == 200, response.text
    assert response.json()["content"]["id"] == entry_id
    assert response.json()["content"][field] == expected
    async with db_session_manager.session() as session:
        affects = (await session.exec(select(PtoAffectEntryRecord))).all()
        assert len(affects) == 1
        assert affects[0].note == "preserve"
        transactions = (await session.exec(select(PtoTransactionRecord))).all()
        assert len(transactions) == (0 if route == "remote-works" else 2)
        if transactions:
            assert transactions[-1].cause.endswith("_update")


async def test_refunds_cancel_excess_then_refill_in_priority_and_support_repeated_updates(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
) -> None:
    await seed(db_session_manager, supabase, annual=100)
    entry_id = create(
        db_client, "work-times", {"date": DAY, "time": 0, "type": 0, "duration": 200}
    )
    path = f"/api/attendance/work-times/{entry_id}"
    for patch, balances, expected_type, value, excess in [
        ({"duration": 100}, (60, 0, 0), 1, 100, 40),
        ({"duration": 150}, (10, 0, 0), 0, 50, 0),
        ({"no_deduction": 1}, (100, 20, 40), 1, 150, 0),
        ({"no_deduction": 0}, (10, 0, 0), 0, 150, 0),
    ]:
        response = db_client.patch(path, json=patch, headers=HEADERS)
        assert response.status_code == 200, response.text
        async with db_session_manager.session() as session:
            bank = await session.get(PtoBankRecord, TEST_PTO_BANK_ID)
            assert (
                bank.annual_balance,
                bank.extended_balance,
                bank.seniority_balance,
            ) == balances
            transactions = (await session.exec(select(PtoTransactionRecord))).all()
            transaction = transactions[-1]
            assert (
                transaction.type,
                transaction.value,
                transaction.exceed_bank_value,
            ) == (expected_type, value, excess)


@pytest.mark.parametrize(
    "duration,balances",
    [(60, (100, 0, 0)), (40, (100, 0, 20)), (10, (100, 10, 40))],
)
async def test_refunds_fill_annual_then_seniority_then_extended_to_original_limits(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
    duration: int,
    balances: tuple[int, int, int],
) -> None:
    await seed(db_session_manager, supabase, annual=100)
    entry_id = create(
        db_client, "work-times", {"date": DAY, "time": 0, "type": 0, "duration": 200}
    )
    response = db_client.patch(
        f"/api/attendance/work-times/{entry_id}",
        json={"duration": duration},
        headers=HEADERS,
    )
    assert response.status_code == 200, response.text
    async with db_session_manager.session() as session:
        bank = await session.get(PtoBankRecord, TEST_PTO_BANK_ID)
        assert (
            bank.annual_balance,
            bank.extended_balance,
            bank.seniority_balance,
        ) == balances
        transaction = (await session.exec(select(PtoTransactionRecord))).all()[-1]
        assert (transaction.type, transaction.value, transaction.exceed_bank_value) == (
            1,
            200 - duration,
            40,
        )


@pytest.mark.parametrize("route,body,patch,field,expected", CASES)
async def test_note_and_empty_updates_do_not_touch_bank_or_ledger(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
    route: str,
    body: dict[str, str | int | None],
    patch: dict[str, str | int | None],
    field: str,
    expected: str | int,
) -> None:
    await seed(db_session_manager, supabase)
    entry_id = create(db_client, route, body | {"note": "old"})
    path = f"/api/attendance/{route}/{entry_id}"
    async with db_session_manager.session() as session:
        before = (await session.get(PtoBankRecord, TEST_PTO_BANK_ID)).model_dump()
        count = len((await session.exec(select(PtoTransactionRecord))).all())
    for update in [{"note": None}, {}]:
        response = db_client.patch(path, json=update, headers=HEADERS)
        assert response.status_code == 200, response.text
    async with db_session_manager.session() as session:
        assert (
            await session.get(PtoBankRecord, TEST_PTO_BANK_ID)
        ).model_dump() == before
        assert len((await session.exec(select(PtoTransactionRecord))).all()) == count
        assert (await session.exec(select(PtoAffectEntryRecord))).one().note == ""


@pytest.mark.parametrize("route,body,patch,field,expected", CASES)
async def test_auth_ownership_and_year_restrictions(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
    route: str,
    body: dict[str, str | int | None],
    patch: dict[str, str | int | None],
    field: str,
    expected: str | int,
) -> None:
    await seed(db_session_manager, supabase)
    entry_id = create(db_client, route, body)
    path = f"/api/attendance/{route}/{entry_id}"
    assert db_client.patch(path, json={}).status_code == 401
    assert (
        db_client.patch(
            f"/api/attendance/{route}/{uuid4()}", json={}, headers=HEADERS
        ).status_code
        == 404
    )
    assert (
        db_client.patch(
            path, json={"date": f"{date.today().year + 1}-06-15"}, headers=HEADERS
        ).status_code
        == 422
    )
    assert (
        db_client.patch(path, json={"date": None}, headers=HEADERS).status_code == 422
    )
    assert (
        db_client.patch(
            path, json={"owner_id": TEST_USER_ID}, headers=HEADERS
        ).status_code
        == 422
    )
    supabase.auth().register("other-token", user_id=str(uuid4()))
    assert (
        db_client.patch(
            path, json={}, headers={"Authorization": "Bearer other-token"}
        ).status_code
        == 404
    )
    # A matching linked entry of the wrong polymorphic type is also hidden.
    async with db_session_manager.transaction() as session:
        affect = (await session.exec(select(PtoAffectEntryRecord))).one()
        affect.entry_type = "unknown"
    assert db_client.patch(path, json={}, headers=HEADERS).status_code == 404


@pytest.mark.parametrize("route,body,patch,field,expected", CASES)
async def test_conflict_rejects_update_and_preserves_entry(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
    route: str,
    body: dict[str, str | int | None],
    patch: dict[str, str | int | None],
    field: str,
    expected: str | int,
) -> None:
    await seed(db_session_manager, supabase)
    first = create(db_client, route, body)
    second_body = body.copy()
    second_body["start_date" if route == "time-offs" else "date"] = date(
        date.today().year, 6, 16
    ).isoformat()
    second = create(db_client, route, second_body)
    response = db_client.patch(
        f"/api/attendance/{route}/{second}", json={"date": DAY}, headers=HEADERS
    )
    assert response.status_code == 409, response.text
    assert first != second
    async with db_session_manager.session() as session:
        count = len((await session.exec(select(PtoTransactionRecord))).all())
        assert count == (0 if route == "remote-works" else 2)


async def test_inconsistent_restoration_rolls_back_all_writes(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
) -> None:
    await seed(db_session_manager, supabase)
    entry_id = create(
        db_client, "work-times", {"date": DAY, "time": 0, "type": 0, "duration": 60}
    )
    async with db_session_manager.transaction() as session:
        bank = await session.get(PtoBankRecord, TEST_PTO_BANK_ID)
        bank.original_annual_balance = bank.annual_balance
        bank.original_extended_balance = 0
        bank.original_seniority_balance = 0
    response = db_client.patch(
        f"/api/attendance/work-times/{entry_id}",
        json={"duration": 30, "note": "rolled back"},
        headers=HEADERS,
    )
    assert response.status_code == 409
    assert response.json()["content"]["error"]["code"] == "pto_adjustment_conflict"
    async with db_session_manager.session() as session:
        assert (await session.get(WorkTimeEntryRecord, UUID(entry_id))).duration == 60
        assert (await session.exec(select(PtoAffectEntryRecord))).one().note == ""
        assert len((await session.exec(select(PtoTransactionRecord))).all()) == 1


async def test_past_year_edits_blocked_including_notes(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
) -> None:
    await seed(db_session_manager, supabase)
    entry_id = create(
        db_client, "work-times", {"date": DAY, "time": 0, "type": 0, "duration": 60}
    )
    async with db_session_manager.transaction() as session:
        entry = await session.get(WorkTimeEntryRecord, UUID(entry_id))
        entry.date = entry.date.replace(year=date.today().year - 1)
    for patch in [{}, {"note": "new"}, {"date": DAY}]:
        response = db_client.patch(
            f"/api/attendance/work-times/{entry_id}", json=patch, headers=HEADERS
        )
        assert response.status_code == 409
        assert (
            response.json()["content"]["error"]["code"]
            == "past_year_entry_not_editable"
        )


async def test_leave_interval_validated_after_merge_and_normalization(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
) -> None:
    await seed(db_session_manager, supabase)
    entry_id = create(
        db_client, "leave-works", {"date": DAY, "start": "09:00", "end": "10:00"}
    )
    response = db_client.patch(
        f"/api/attendance/leave-works/{entry_id}",
        json={"start": "10:00:59"},
        headers=HEADERS,
    )
    assert response.status_code == 422
    assert response.json()["content"]["error"]["code"] == "validation_error"


@pytest.mark.parametrize("route,body,patch,field,expected", CASES)
async def test_same_year_date_changes_preserve_penalty(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
    route: str,
    body: dict[str, str | int | None],
    patch: dict[str, str | int | None],
    field: str,
    expected: str | int,
) -> None:
    await seed(db_session_manager, supabase)
    entry_id = create(db_client, route, body)
    new_date = date(date.today().year, 12, 31).isoformat()
    response = db_client.patch(
        f"/api/attendance/{route}/{entry_id}", json={"date": new_date}, headers=HEADERS
    )
    assert response.status_code == 200, response.text
    assert response.json()["content"]["date"] == new_date
    async with db_session_manager.session() as session:
        assert len((await session.exec(select(PtoTransactionRecord))).all()) == (
            0 if route == "remote-works" else 1
        )


async def test_pure_excess_reduction_does_not_invent_bank_balance(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
) -> None:
    await seed(db_session_manager, supabase, annual=100)
    entry_id = create(
        db_client, "work-times", {"date": DAY, "time": 0, "type": 0, "duration": 200}
    )
    response = db_client.patch(
        f"/api/attendance/work-times/{entry_id}",
        json={"duration": 180},
        headers=HEADERS,
    )
    assert response.status_code == 200
    async with db_session_manager.session() as session:
        bank = await session.get(PtoBankRecord, TEST_PTO_BANK_ID)
        assert (
            bank.annual_balance == bank.extended_balance == bank.seniority_balance == 0
        )
        transaction = (await session.exec(select(PtoTransactionRecord))).all()[-1]
        assert (transaction.value, transaction.exceed_bank_value, transaction.type) == (
            20,
            20,
            1,
        )


@pytest.mark.parametrize("has_profile", [False, True])
async def test_enabling_deduction_creates_missing_current_bank_or_rolls_back(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
    has_profile: bool,
) -> None:
    supabase.auth().register("update-token", user_id=TEST_USER_ID)
    if has_profile:
        async with db_session_manager.transaction() as session:
            session.add(make_profile_record(work_start_date=date.today()))
    entry_id = create(
        db_client,
        "work-times",
        {"date": DAY, "time": 0, "type": 0, "duration": 60, "no_deduction": 1},
    )
    response = db_client.patch(
        f"/api/attendance/work-times/{entry_id}",
        json={"no_deduction": 0},
        headers=HEADERS,
    )
    assert response.status_code == (200 if has_profile else 404), response.text
    async with db_session_manager.session() as session:
        assert (
            await session.exec(select(PtoAffectEntryRecord))
        ).one().no_deduction == (0 if has_profile else 1)
        assert len((await session.exec(select(PtoBankRecord))).all()) == int(
            has_profile
        )
        assert len((await session.exec(select(PtoTransactionRecord))).all()) == int(
            has_profile
        )


async def test_future_year_entry_is_editable_but_missing_future_bank_cannot_be_created(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
) -> None:
    await seed(db_session_manager, supabase)
    future_day = date(date.today().year + 1, 6, 15).isoformat()
    entry_id = create(
        db_client,
        "work-times",
        {"date": future_day, "time": 0, "type": 0, "duration": 60, "no_deduction": 1},
    )
    path = f"/api/attendance/work-times/{entry_id}"
    assert (
        db_client.patch(path, json={"note": "future"}, headers=HEADERS).status_code
        == 200
    )
    response = db_client.patch(path, json={"no_deduction": 0}, headers=HEADERS)
    assert response.status_code == 404
    assert response.json()["content"]["error"]["code"] == "pto_bank_not_found"


@pytest.mark.parametrize("route", [case[0] for case in CASES])
def test_patch_openapi_contract(db_client: TestClient, route: str) -> None:
    schema = db_client.app.openapi()
    operation = schema["paths"][f"/api/attendance/{route}/{{entry_id}}"]["patch"]
    assert operation["security"]
    assert set(operation["responses"]) == {"200", "401", "404", "409", "422"}
    for status, response in operation["responses"].items():
        envelope = response["content"]["application/json"]["schema"]
        assert set(envelope["properties"]) == {"ok", "content"}
        assert envelope["properties"]["ok"]["const"] == (status == "200")


@pytest.mark.parametrize("route,body", [(case[0], case[1]) for case in CASES[1:]])
@pytest.mark.parametrize("title", ["Clinic appointment", "Untitled", ""])
async def test_titles_persist_without_changing_pto(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
    route: str,
    body: dict[str, str | int | None],
    title: str,
) -> None:
    await seed(db_session_manager, supabase)
    payload = body | ({"title": title} if title != "Untitled" else {})
    entry_id = create(db_client, route, payload)
    path = f"/api/attendance/{route}/{entry_id}"
    async with db_session_manager.session() as session:
        assert (await session.exec(select(PtoAffectEntryRecord))).one().title == title
        before = (await session.get(PtoBankRecord, TEST_PTO_BANK_ID)).model_dump()
        ledger = [
            row.model_dump()
            for row in (await session.exec(select(PtoTransactionRecord))).all()
        ]
    for update in [{"title": "Updated title"}, {}, {"note": "Another note"}]:
        response = db_client.patch(path, json=update, headers=HEADERS)
        assert response.status_code == 200, response.text
        assert "title" not in response.json()["content"]
    assert (
        db_client.patch(path, json={"title": None}, headers=HEADERS).status_code == 422
    )
    async with db_session_manager.session() as session:
        assert (
            await session.exec(select(PtoAffectEntryRecord))
        ).one().title == "Updated title"
        assert (
            await session.get(PtoBankRecord, TEST_PTO_BANK_ID)
        ).model_dump() == before
        assert [
            row.model_dump()
            for row in (await session.exec(select(PtoTransactionRecord))).all()
        ] == ledger


@pytest.mark.parametrize("route,body", [(case[0], case[1]) for case in CASES[1:]])
def test_create_rejects_null_titles(
    db_client: TestClient,
    supabase: SqliteSupabasePort,
    route: str,
    body: dict[str, str | int | None],
) -> None:
    supabase.auth().register("update-token", user_id=TEST_USER_ID)
    response = db_client.post(
        f"/api/attendance/{route}", json=body | {"title": None}, headers=HEADERS
    )
    assert response.status_code == 422


async def test_check_in_title_tracks_date(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
) -> None:
    await seed(db_session_manager, supabase)
    entry_id = create(db_client, "check-ins", {"date": DAY, "time": "09:00"})
    async with db_session_manager.session() as session:
        assert (
            await session.exec(select(PtoAffectEntryRecord))
        ).one().title == f"Check-in on {DAY}"
    new_date = date(date.today().year, 6, 16).isoformat()
    path = f"/api/attendance/check-ins/{entry_id}"
    response = db_client.patch(path, json={"date": new_date}, headers=HEADERS)
    assert response.status_code == 200, response.text
    assert (
        db_client.patch(
            path, json={"title": "Client title"}, headers=HEADERS
        ).status_code
        == 422
    )
    async with db_session_manager.session() as session:
        assert (
            await session.exec(select(PtoAffectEntryRecord))
        ).one().title == f"Check-in on {new_date}"


async def test_time_off_range_shares_title(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
) -> None:
    await seed(db_session_manager, supabase)
    response = db_client.post(
        "/api/attendance/time-offs",
        json={
            "start_date": DAY,
            "end_date": date(date.today().year, 6, 17).isoformat(),
            "type": 0,
            "title": "Summer trip",
        },
        headers=HEADERS,
    )
    assert response.status_code == 200, response.text
    async with db_session_manager.session() as session:
        affects = (await session.exec(select(PtoAffectEntryRecord))).all()
        assert len(affects) == 3
        assert all(affect.title == "Summer trip" for affect in affects)
