from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from app.database import (
    DbSessionManager,
    CheckInEntryRecord,
    TimeOffEntryRecord,
    RemoteWorkEntryRecord,
    WorkTimeEntryRecord,
    LeaveWorkEntryRecord,
    PtoAffectEntryRecord,
    PtoBankRecord,
    PtoTransactionRecord,
    WorkdayExceptionRecord,
)
from tests.factories.database_records import (
    TEST_USER_ID,
    make_profile_record,
    make_pto_bank_record,
)
from tests.fakes.sqlite_supabase import SqliteSupabasePort

MONDAY = date(date.today().year, 6, 1)
MONDAY += timedelta(days=(7 - MONDAY.weekday()) % 7)
SATURDAY = MONDAY + timedelta(days=5)
HEADERS = {"Authorization": "Bearer calendar-token"}
CASES = [
    ("check-ins", {"time": "09:00", "no_deduction": 1}),
    ("time-offs", {"type": 0, "no_deduction": 1}),
    ("remote-works", {"type": 0}),
    ("work-times", {"time": 0, "type": 0, "duration": 30, "no_deduction": 1}),
    ("leave-works", {"start": "09:00", "end": "10:00", "no_deduction": 1}),
]


def payload(route: str, body: dict[str, str | int], day: date) -> dict[str, str | int]:
    return {**body, "start_date" if route == "time-offs" else "date": day.isoformat()}


async def seed(manager: DbSessionManager, supabase: SqliteSupabasePort) -> None:
    supabase.auth().register("calendar-token", user_id=TEST_USER_ID)
    async with manager.transaction() as session:
        session.add(make_profile_record())
        session.add(make_pto_bank_record(year=MONDAY.year, annual_balance=5000))


async def exception(
    manager: DbSessionManager, day: date, kind: int, period: int = 0
) -> None:
    async with manager.transaction() as session:
        session.add(
            WorkdayExceptionRecord(
                date=day, type=kind, time=period, title="Private calendar title"
            )
        )


async def snapshot(manager: DbSessionManager) -> list[list[dict[str, object]]]:
    async with manager.session() as session:
        return [
            [
                record.model_dump()
                for record in (await session.exec(select(model))).all()
            ]
            for model in (
                PtoAffectEntryRecord,
                PtoBankRecord,
                PtoTransactionRecord,
                CheckInEntryRecord,
                TimeOffEntryRecord,
                RemoteWorkEntryRecord,
                WorkTimeEntryRecord,
                LeaveWorkEntryRecord,
            )
        ]


@pytest.mark.parametrize("route,body", CASES)
@pytest.mark.parametrize(
    "weekend,kind,allowed",
    [(False, None, True), (True, None, False), (True, 0, True), (False, 1, False)],
)
async def test_create_calendar_rules(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
    route: str,
    body: dict[str, str | int],
    weekend: bool,
    kind: int | None,
    allowed: bool,
) -> None:
    await seed(db_session_manager, supabase)
    day = SATURDAY if weekend else MONDAY
    if kind is not None:
        await exception(db_session_manager, day, kind)
    before = await snapshot(db_session_manager)
    response = db_client.post(
        f"/api/attendance/{route}", json=payload(route, body, day), headers=HEADERS
    )
    assert response.status_code == (200 if allowed else 409), response.text
    if not allowed:
        assert response.json()["content"]["error"]["code"] == "attendance_non_workday"
        assert await snapshot(db_session_manager) == before
        assert "Private calendar title" not in response.text


@pytest.mark.parametrize("route,body", CASES)
@pytest.mark.parametrize(
    "weekend,kind,allowed",
    [(False, None, True), (True, None, False), (True, 0, True), (False, 1, False)],
)
async def test_update_calendar_rules(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
    route: str,
    body: dict[str, str | int],
    weekend: bool,
    kind: int | None,
    allowed: bool,
) -> None:
    await seed(db_session_manager, supabase)
    response = db_client.post(
        f"/api/attendance/{route}", json=payload(route, body, MONDAY), headers=HEADERS
    )
    assert response.status_code == 200, response.text
    content = response.json()["content"]
    entry_id = (content[0] if isinstance(content, list) else content)["id"]
    day = SATURDAY if weekend else MONDAY
    if kind is not None:
        await exception(db_session_manager, day, kind)
    before = await snapshot(db_session_manager)
    response = db_client.patch(
        f"/api/attendance/{route}/{entry_id}",
        json={"date": day.isoformat(), "note": "Changed"},
        headers=HEADERS,
    )
    assert response.status_code == (200 if allowed else 409), response.text
    if not allowed:
        assert response.json()["content"]["error"]["code"] == "attendance_non_workday"
        assert await snapshot(db_session_manager) == before


@pytest.mark.parametrize("route,body", CASES)
async def test_metadata_update_checks_current_calendar(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
    route: str,
    body: dict[str, str | int],
) -> None:
    await seed(db_session_manager, supabase)
    response = db_client.post(
        f"/api/attendance/{route}", json=payload(route, body, MONDAY), headers=HEADERS
    )
    content = response.json()["content"]
    entry_id = (content[0] if isinstance(content, list) else content)["id"]
    await exception(db_session_manager, MONDAY, 1)
    before = await snapshot(db_session_manager)
    response = db_client.patch(
        f"/api/attendance/{route}/{entry_id}", json={"note": "Changed"}, headers=HEADERS
    )
    assert response.status_code == 409
    assert await snapshot(db_session_manager) == before
    # Moving the entry to an eligible date remains possible.
    response = db_client.patch(
        f"/api/attendance/{route}/{entry_id}",
        json={"date": (MONDAY + timedelta(days=1)).isoformat()},
        headers=HEADERS,
    )
    assert response.status_code == 200, response.text


async def test_range_rejection_is_atomic(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
) -> None:
    await seed(db_session_manager, supabase)
    before = await snapshot(db_session_manager)
    response = db_client.post(
        "/api/attendance/time-offs",
        json={
            "start_date": (SATURDAY - timedelta(days=1)).isoformat(),
            "end_date": SATURDAY.isoformat(),
            "type": 0,
        },
        headers=HEADERS,
    )
    assert response.status_code == 409
    assert await snapshot(db_session_manager) == before


def test_openapi_documents_calendar_conflicts(db_client: TestClient) -> None:
    schema = db_client.app.openapi()
    for route, _ in CASES:
        for method, suffix in (("post", ""), ("patch", "/{entry_id}")):
            operation = schema["paths"][f"/api/attendance/{route}{suffix}"][method]
            response = operation["responses"]["409"]
            assert "attendance_non_workday" in str(response)
            assert "HOLIDAY exceptions taking precedence" in operation["description"]
            assert (
                "ok" in response["content"]["application/json"]["schema"]["properties"]
            )


@pytest.mark.parametrize("route", ["time-offs", "remote-works"])
@pytest.mark.parametrize("entry_period", [0, 1, 2])
@pytest.mark.parametrize("method", ["POST", "PATCH"])
@pytest.mark.parametrize(
    "weekend,kind,exception_periods,available_periods",
    [
        (False, 1, [0], set()),
        (False, 1, [1], {2}),
        (False, 1, [2], {1}),
        (True, 0, [0], {0, 1, 2}),
        (True, 0, [1], {1}),
        (True, 0, [2], {2}),
        (True, 0, [1, 2], {0, 1, 2}),
    ],
)
async def test_full_and_half_day_calendar_coverage(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
    route: str,
    entry_period: int,
    method: str,
    weekend: bool,
    kind: int,
    exception_periods: list[int],
    available_periods: set[int],
) -> None:
    await seed(db_session_manager, supabase)
    body: dict[str, str | int] = {"type": entry_period}
    if route == "time-offs":
        body["no_deduction"] = 1
    path = f"/api/attendance/{route}"
    day = SATURDAY if weekend else MONDAY
    request_body = payload(route, body, day)
    if method == "PATCH":
        original = db_client.post(
            path, json=payload(route, body, MONDAY + timedelta(days=1)), headers=HEADERS
        )
        assert original.status_code == 200, original.text
        content = original.json()["content"]
        entry_id = (content[0] if isinstance(content, list) else content)["id"]
        path += f"/{entry_id}"
        request_body = {"date": day.isoformat(), "note": "Calendar update"}
    for period in exception_periods:
        await exception(db_session_manager, day, kind, period)
    before = await snapshot(db_session_manager)
    response = db_client.request(method, path, json=request_body, headers=HEADERS)
    allowed = entry_period in available_periods
    assert response.status_code == (200 if allowed else 409), response.text
    if allowed:
        content = response.json()["content"]
        entry = content[0] if isinstance(content, list) else content
        assert entry["date"] == day.isoformat()
        assert entry["type"] == entry_period
    else:
        assert response.json()["content"]["error"]["code"] == "attendance_non_workday"
        assert await snapshot(db_session_manager) == before


@pytest.mark.parametrize("route", ["time-offs", "remote-works"])
@pytest.mark.parametrize(
    "original_period,replacement_period,holiday_period,allowed",
    [
        (1, 0, 2, False),
        (2, 0, 1, False),
        (1, 2, 1, True),
        (2, 1, 2, True),
        (1, 2, 2, False),
        (2, 1, 1, False),
        (0, 1, 2, True),
        (0, 2, 1, True),
    ],
)
async def test_patch_validates_replacement_period(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
    route: str,
    original_period: int,
    replacement_period: int,
    holiday_period: int,
    allowed: bool,
) -> None:
    await seed(db_session_manager, supabase)
    body: dict[str, str | int] = {"type": original_period}
    if route == "time-offs":
        body["no_deduction"] = 1
    path = f"/api/attendance/{route}"
    created = db_client.post(path, json=payload(route, body, MONDAY), headers=HEADERS)
    assert created.status_code == 200, created.text
    content = created.json()["content"]
    entry_id = (content[0] if isinstance(content, list) else content)["id"]
    await exception(db_session_manager, MONDAY, 1, holiday_period)
    before = await snapshot(db_session_manager)
    response = db_client.patch(
        f"{path}/{entry_id}", json={"type": replacement_period}, headers=HEADERS
    )
    assert response.status_code == (200 if allowed else 409), response.text
    if allowed:
        assert response.json()["content"]["type"] == replacement_period
    else:
        assert response.json()["content"]["error"]["code"] == "attendance_non_workday"
        assert await snapshot(db_session_manager) == before


@pytest.mark.parametrize(
    "route,body,changes,holiday_period,allowed",
    [
        ("work-times", {"time": 0, "type": 0, "duration": 30}, {"time": 1}, 1, True),
        ("work-times", {"time": 0, "type": 0, "duration": 30}, {"time": 1}, 2, False),
        ("work-times", {"time": 1, "type": 0, "duration": 30}, {"time": 0}, 2, True),
        ("work-times", {"time": 1, "type": 0, "duration": 30}, {"time": 0}, 1, False),
        (
            "leave-works",
            {"start": "09:00", "end": "10:00"},
            {"start": "14:00", "end": "15:00"},
            1,
            True,
        ),
        (
            "leave-works",
            {"start": "09:00", "end": "10:00"},
            {"start": "14:00", "end": "15:00"},
            2,
            False,
        ),
        ("leave-works", {"start": "11:00", "end": "12:00"}, {"end": "14:00"}, 2, False),
        ("leave-works", {"start": "11:00", "end": "14:00"}, {"end": "12:00"}, 2, True),
        ("leave-works", {"start": "11:00", "end": "12:00"}, {"end": "13:30"}, 2, True),
    ],
)
async def test_patch_validates_replacement_shift_or_interval(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
    route: str,
    body: dict[str, str | int],
    changes: dict[str, str | int],
    holiday_period: int,
    allowed: bool,
) -> None:
    await seed(db_session_manager, supabase)
    path = f"/api/attendance/{route}"
    created = db_client.post(
        path, json=payload(route, {**body, "no_deduction": 1}, MONDAY), headers=HEADERS
    )
    assert created.status_code == 200, created.text
    entry_id = created.json()["content"]["id"]
    await exception(db_session_manager, MONDAY, 1, holiday_period)
    before = await snapshot(db_session_manager)
    response = db_client.patch(f"{path}/{entry_id}", json=changes, headers=HEADERS)
    assert response.status_code == (200 if allowed else 409), response.text
    if allowed:
        for field, expected in changes.items():
            actual = response.json()["content"][field]
            assert actual == (
                expected + ":00" if isinstance(expected, str) else expected
            )
    else:
        assert response.json()["content"]["error"]["code"] == "attendance_non_workday"
        assert await snapshot(db_session_manager) == before


@pytest.mark.parametrize("holiday_period", [0, 1, 2])
async def test_time_off_range_rejects_any_holiday_period_atomically(
    db_client: TestClient,
    db_session_manager: DbSessionManager,
    supabase: SqliteSupabasePort,
    holiday_period: int,
) -> None:
    await seed(db_session_manager, supabase)
    await exception(db_session_manager, MONDAY + timedelta(days=1), 1, holiday_period)
    before = await snapshot(db_session_manager)
    response = db_client.post(
        "/api/attendance/time-offs",
        json={
            "start_date": MONDAY.isoformat(),
            "end_date": (MONDAY + timedelta(days=2)).isoformat(),
            "type": 0,
            "no_deduction": 1,
        },
        headers=HEADERS,
    )
    assert response.status_code == 409
    assert response.json()["content"]["error"]["code"] == "attendance_non_workday"
    assert await snapshot(db_session_manager) == before
