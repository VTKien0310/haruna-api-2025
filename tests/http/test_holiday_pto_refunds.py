from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlmodel import select

from app.database import (
    CheckInEntryRecord,
    DbSessionManager,
    PtoAffectEntryRecord,
    PtoBankRecord,
    PtoTransactionRecord,
    UserSpecialPermissionRecord,
    WorkdayExceptionRecord,
)
from app.features.attendance.services import GetWorkdayExceptionTodayService
from tests.factories.database_records import (
    TEST_USER_UUID,
    make_profile_record,
    make_pto_bank_record,
)
from tests.fakes.sqlite_supabase import SqliteSupabasePort

BASE = "/api/attendance/workday-exceptions"
HEADERS = {"Authorization": "Bearer calendar-manager"}
TODAY = GetWorkdayExceptionTodayService().handle()
DAY = TODAY + timedelta(days=(7 - TODAY.weekday()) % 7)
OTHER_USER = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
CASES = [
    ("check-ins", {"time": "09:30"}, 90, {1}),
    ("time-offs", {"type": 0}, 480, {1, 2}),
    ("time-offs", {"type": 1}, 240, {1}),
    ("time-offs", {"type": 2}, 240, {2}),
    ("remote-works", {"type": 1}, 0, {1}),
    ("remote-works", {"type": 2}, 0, {2}),
    ("work-times", {"time": 0, "type": 0, "duration": 30}, 30, {1}),
    ("work-times", {"time": 1, "type": 0, "duration": 30}, 30, {2}),
    ("leave-works", {"start": "11:00", "end": "12:00"}, 60, {1}),
    ("leave-works", {"start": "13:30", "end": "14:00"}, 30, {2}),
    ("leave-works", {"start": "11:00", "end": "14:00"}, 180, {1, 2}),
    ("leave-works", {"start": "12:00", "end": "13:30"}, 90, {1, 2}),
]


async def seed(
    manager: DbSessionManager,
    supabase: SqliteSupabasePort,
    *,
    owners: tuple[UUID, ...] = (TEST_USER_UUID,),
    annual: int = 6000,
) -> None:
    supabase.auth().register("calendar-manager", user_id=str(TEST_USER_UUID))
    async with manager.transaction() as session:
        session.add(UserSpecialPermissionRecord(user_id=TEST_USER_UUID, permission=0))
        for owner in owners:
            supabase.auth().register(str(owner), user_id=str(owner))
            session.add(
                make_profile_record(id=uuid4(), user_id=owner, work_start_date=TODAY)
            )
            session.add(
                make_pto_bank_record(
                    id=uuid4(),
                    owner_id=owner,
                    year=DAY.year,
                    annual_balance=annual,
                    original_annual_balance=annual,
                    seniority_balance=0,
                    original_seniority_balance=0,
                )
            )


def create_entry(
    client: TestClient,
    route: str,
    body: dict[str, str | int],
    owner: UUID = TEST_USER_UUID,
    *,
    later: bool = False,
) -> str:
    day = DAY + timedelta(days=7) if later else DAY
    response = client.post(
        f"/api/attendance/{route}",
        json={
            **body,
            "start_date" if route == "time-offs" else "date": day.isoformat(),
        },
        headers={"Authorization": f"Bearer {owner}"},
    )
    assert response.status_code == 200, response.text
    content = response.json()["content"]
    return (content[0] if isinstance(content, list) else content)["id"]


def create_holiday(client: TestClient, period: int = 0) -> Response:
    return client.post(
        BASE,
        json={"type": 1, "date": DAY.isoformat(), "time": period, "title": "Holiday"},
        headers=HEADERS,
    )


async def snapshot(manager: DbSessionManager) -> list[list[dict[str, object]]]:
    async with manager.session() as session:
        return [
            [
                row.model_dump()
                for row in (await session.exec(select(model).order_by(model.id))).all()
            ]
            for model in (PtoAffectEntryRecord, PtoBankRecord, PtoTransactionRecord)
        ]


@pytest.mark.parametrize("route,body,penalty,shifts", CASES)
@pytest.mark.parametrize("period", [0, 1, 2])
async def test_holiday_refunds_only_matching_entries_and_delete_keeps_refunds(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
    route: str,
    body: dict[str, str | int],
    penalty: int,
    shifts: set[int],
    period: int,
) -> None:
    await seed(db_session_manager, supabase)
    create_entry(db_client, route, body)
    response = create_holiday(db_client, period)
    assert response.status_code == 201, response.text
    matches = period == 0 or period in shifts
    state = await snapshot(db_session_manager)
    affects, banks, transactions = state
    assert affects[0]["no_deduction"] == int(matches or route == "remote-works")
    assert banks[0]["annual_balance"] == 6000 - (0 if matches else penalty)
    increases = [t for t in transactions if t["type"] == 1]
    assert [t["value"] for t in increases] == ([penalty] if matches and penalty else [])
    assert affects[0]["note"] == ""
    assert (
        db_client.delete(
            f"{BASE}/{response.json()['content']['id']}", headers=HEADERS
        ).status_code
        == 204
    )
    assert await snapshot(db_session_manager) == state
    # Recreating a holiday does not refund an already repaid penalty.
    assert create_holiday(db_client, period).status_code == 201
    assert await snapshot(db_session_manager) == state


async def test_refunds_every_owner_but_not_other_dates(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
) -> None:
    await seed(db_session_manager, supabase, owners=(TEST_USER_UUID, OTHER_USER))
    for owner in (TEST_USER_UUID, OTHER_USER):
        create_entry(db_client, "check-ins", {"time": "09:30"}, owner)
        create_entry(db_client, "check-ins", {"time": "09:00"}, owner, later=True)
    assert create_holiday(db_client).status_code == 201
    affects, banks, transactions = await snapshot(db_session_manager)
    assert sum(row["no_deduction"] for row in affects) == 2
    assert [bank["annual_balance"] for bank in banks] == [5940, 5940]
    assert sorted(t["value"] for t in transactions if t["type"] == 1) == [90, 90]


async def test_refund_uses_remaining_ledger_penalty_and_cancels_excess(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
) -> None:
    await seed(db_session_manager, supabase, annual=30)
    entry_id = create_entry(db_client, "check-ins", {"time": "09:30"})
    response = db_client.patch(
        f"/api/attendance/check-ins/{entry_id}",
        json={"time": "09:00"},
        headers={"Authorization": f"Bearer {TEST_USER_UUID}"},
    )
    assert response.status_code == 200, response.text
    assert create_holiday(db_client).status_code == 201
    _, banks, transactions = await snapshot(db_session_manager)
    assert banks[0]["annual_balance"] == 30
    increases = sorted(
        (t["value"], t["exceed_bank_value"]) for t in transactions if t["type"] == 1
    )
    assert increases == [(30, 30), (60, 30)]
    assert all(
        t["cause"] == "check_in_entries_update" for t in transactions if t["type"] == 1
    )


async def test_manual_and_zero_penalty_entries_need_no_refund(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
) -> None:
    await seed(db_session_manager, supabase)
    create_entry(db_client, "check-ins", {"time": "08:00"})
    create_entry(
        db_client,
        "time-offs",
        {"type": 0, "no_deduction": 1, "note": "Manual", "title": "Keep"},
    )
    assert create_holiday(db_client).status_code == 201
    affects, banks, transactions = await snapshot(db_session_manager)
    assert all(row["no_deduction"] == 1 for row in affects)
    assert any(row["title"] == "Keep" and row["note"] == "Manual" for row in affects)
    assert transactions == []
    assert banks[0]["annual_balance"] == 6000


@pytest.mark.parametrize(
    "failure", ["negative_history", "no_capacity", "zero_net_invalid_excess"]
)
async def test_failure_rolls_back_holiday_and_all_owners(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
    failure: str,
) -> None:
    await seed(db_session_manager, supabase, owners=(TEST_USER_UUID, OTHER_USER))
    for owner in (TEST_USER_UUID, OTHER_USER):
        create_entry(db_client, "check-ins", {"time": "09:30"}, owner)
    async with db_session_manager.transaction() as session:
        # Corrupt the entry processed last so rollback also covers prior refunds.
        affects = (
            await session.exec(
                select(PtoAffectEntryRecord).order_by(PtoAffectEntryRecord.id)
            )
        ).all()
        last = affects[-1]
        transaction = (
            await session.exec(
                select(PtoTransactionRecord).where(
                    PtoTransactionRecord.entry_id == last.id
                )
            )
        ).one()
        if failure == "negative_history":
            transaction.value = -1
        elif failure == "zero_net_invalid_excess":
            transaction.value = 0
            transaction.exceed_bank_value = 1
        else:
            bank = (
                await session.exec(
                    select(PtoBankRecord).where(PtoBankRecord.owner_id == last.owner_id)
                )
            ).one()
            bank.original_annual_balance = bank.annual_balance
    before = await snapshot(db_session_manager)
    response = create_holiday(db_client)
    assert response.status_code == 409, response.text
    assert response.json()["content"]["error"]["code"] == "pto_adjustment_conflict"
    assert await snapshot(db_session_manager) == before
    async with db_session_manager.session() as session:
        assert (await session.exec(select(WorkdayExceptionRecord))).all() == []


async def test_workday_creation_has_no_pto_effect(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
) -> None:
    await seed(db_session_manager, supabase)
    create_entry(db_client, "check-ins", {"time": "09:30"})
    before = await snapshot(db_session_manager)
    saturday = DAY + timedelta(days=5)
    # Seed an entry on that weekend to ensure WORKDAY creation does not refund it.

    async with db_session_manager.transaction() as session:
        entry = (await session.exec(select(CheckInEntryRecord))).one()
        entry.date = saturday
    response = db_client.post(
        BASE,
        json={"type": 0, "date": saturday.isoformat(), "time": 0, "title": "Work"},
        headers=HEADERS,
    )
    assert response.status_code == 201, response.text
    assert await snapshot(db_session_manager) == before


async def test_complementary_holidays_do_not_duplicate_refunds(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
) -> None:
    await seed(db_session_manager, supabase)
    create_entry(db_client, "time-offs", {"type": 0})
    morning = create_holiday(db_client, 1)
    assert morning.status_code == 201
    before = await snapshot(db_session_manager)
    afternoon = create_holiday(db_client, 2)
    assert afternoon.status_code == 201
    rejected = create_holiday(db_client, 0)
    assert rejected.status_code == 409
    assert rejected.json()["content"]["error"]["code"] == "workday_exception_overlap"
    assert await snapshot(db_session_manager) == before
    assert (
        db_client.delete(
            f"{BASE}/{morning.json()['content']['id']}", headers=HEADERS
        ).status_code
        == 204
    )
    assert await snapshot(db_session_manager) == before


async def test_overlap_rejection_does_not_refund_uncovered_entries(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
) -> None:
    await seed(db_session_manager, supabase)
    create_entry(db_client, "time-offs", {"type": 1})
    create_entry(db_client, "time-offs", {"type": 2})
    assert create_holiday(db_client, 1).status_code == 201
    before = await snapshot(db_session_manager)
    response = create_holiday(db_client, 0)
    assert response.status_code == 409
    assert response.json()["content"]["error"]["code"] == "workday_exception_overlap"
    assert await snapshot(db_session_manager) == before
    async with db_session_manager.session() as session:
        exceptions = (await session.exec(select(WorkdayExceptionRecord))).all()
        assert len(exceptions) == 1
        assert exceptions[0].time == 1
