from datetime import date, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import create_app
from app.database import (
    DbSessionManager,
    UserSpecialPermissionRecord,
    WorkdayExceptionRecord,
)
from app.features.attendance.services import GetWorkdayExceptionTodayService
from tests.factories.database_records import TEST_USER_ID, TEST_USER_UUID
from tests.fakes.sqlite_supabase import SqliteSupabasePort

BASE = "/api/attendance/workday-exceptions"
HEADERS = {"Authorization": "Bearer token-1"}


def next_weekday() -> date:
    day = GetWorkdayExceptionTodayService().handle()
    return day + timedelta(days=7 - day.weekday() if day.weekday() >= 5 else 0)


def next_weekend() -> date:
    day = GetWorkdayExceptionTodayService().handle()
    return day + timedelta(days=(5 - day.weekday()) % 7)


def payload(day: date | None = None) -> dict[str, str | int]:
    return {
        "date": (day or next_weekday()).isoformat(),
        "type": 1,
        "time": 0,
        "title": "Holiday",
    }


@pytest.fixture
async def manager(
    db_session_manager: DbSessionManager, supabase: SqliteSupabasePort
) -> DbSessionManager:
    supabase.auth().register("token-1", user_id=TEST_USER_ID)
    async with db_session_manager.transaction() as session:
        session.add(UserSpecialPermissionRecord(user_id=TEST_USER_UUID, permission=0))
    return db_session_manager


@pytest.mark.parametrize(
    "method,suffix,body",
    [
        ("POST", "", payload()),
        ("GET", "", None),
        ("GET", f"/{uuid4()}", None),
        ("DELETE", f"/{uuid4()}", None),
    ],
)
async def test_access_is_required(
    db_client: TestClient,
    supabase: SqliteSupabasePort,
    method: str,
    suffix: str,
    body: dict | None,
) -> None:
    assert db_client.request(method, BASE + suffix, json=body).status_code == 401
    supabase.auth().register("token-1", user_id=TEST_USER_ID)
    response = db_client.request(method, BASE + suffix, json=body, headers=HEADERS)
    assert response.status_code == 403
    assert response.json()["content"]["error"]["code"] == "forbidden"


async def test_create_read_delete_and_duplicate_rejection(
    db_client: TestClient, manager: DbSessionManager
) -> None:
    first = db_client.post(BASE, json=payload(), headers=HEADERS)
    assert first.status_code == 201
    original = first.json()["content"]
    path = f"{BASE}/{original['id']}"
    UUID(original["id"])
    stored = db_client.get(path, headers=HEADERS).json()["content"]
    # SQLite drops timezone information on reload; PostgreSQL retains it.
    assert stored == {
        key: value.removesuffix("Z") if key.endswith("_at") else value
        for key, value in original.items()
    }
    assert db_client.post(BASE, json=payload(), headers=HEADERS).status_code == 409
    listing = db_client.get(BASE, headers=HEADERS).json()["content"]
    assert len(listing) == 1
    assert listing == sorted(listing, key=lambda item: (item["date"], item["id"]))
    deleted = db_client.delete(path, headers=HEADERS)
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert db_client.get(path, headers=HEADERS).status_code == 404


async def test_past_records_are_readable_and_immutable(
    db_client: TestClient, manager: DbSessionManager
) -> None:
    yesterday = GetWorkdayExceptionTodayService().handle() - timedelta(days=1)
    async with manager.transaction() as session:
        record = WorkdayExceptionRecord(date=yesterday, type=1, time=0, title="Past")
        session.add(record)
        await session.flush()
        exception_id = record.id
    path = f"{BASE}/{exception_id}"
    assert db_client.get(path, headers=HEADERS).status_code == 200
    assert len(db_client.get(BASE, headers=HEADERS).json()["content"]) == 1
    attempts = [
        db_client.post(BASE, json=payload(yesterday), headers=HEADERS),
        db_client.delete(path, headers=HEADERS),
    ]
    for response in attempts:
        assert response.status_code == 409
        assert (
            response.json()["content"]["error"]["code"]
            == "past_workday_exception_immutable"
        )
    async with manager.session() as session:
        records = (await session.exec(select(WorkdayExceptionRecord))).scalars().all()
        assert len(records) == 1
        assert records[0].title == "Past"
        assert records[0].date == yesterday


@pytest.mark.parametrize(
    "changes",
    [
        {"type": 4},
        {"time": -1},
        {"date": "invalid"},
        {"title": "  "},
        {"title": None},
        {"id": str(uuid4())},
    ],
)
async def test_invalid_bodies(
    db_client: TestClient, manager: DbSessionManager, changes: dict
) -> None:
    assert (
        db_client.post(BASE, json=payload() | changes, headers=HEADERS).status_code
        == 422
    )


@pytest.mark.parametrize("method", ["GET", "DELETE"])
async def test_missing_and_invalid_ids(
    db_client: TestClient, manager: DbSessionManager, method: str
) -> None:
    response = db_client.request(method, f"{BASE}/{uuid4()}", headers=HEADERS)
    assert response.status_code == 404
    assert response.json()["content"]["error"]["code"] == "workday_exception_not_found"
    assert (
        db_client.request(method, f"{BASE}/bad-id", headers=HEADERS).status_code == 422
    )


def test_openapi_contract() -> None:
    schema = create_app().openapi()
    for path, methods in [
        (BASE, ["post", "get"]),
        (BASE + "/{exception_id}", ["get", "delete"]),
    ]:
        for method in methods:
            operation = schema["paths"][path][method]
            assert operation["security"]
            assert "403" in operation["responses"]
            for status, response in operation["responses"].items():
                if status == "204":
                    assert "content" not in response
                elif "application/json" in response.get("content", {}):
                    assert set(
                        response["content"]["application/json"]["schema"]["properties"]
                    ) == {"ok", "content"}
    assert "HTTPValidationError" not in schema["components"]["schemas"]


@pytest.mark.parametrize("weekday", range(7))
@pytest.mark.parametrize("kind", [0, 1])
@pytest.mark.parametrize("period", [0, 1, 2])
async def test_create_requires_exception_for_opposite_schedule(
    db_client: TestClient,
    manager: DbSessionManager,
    weekday: int,
    kind: int,
    period: int,
) -> None:
    today = GetWorkdayExceptionTodayService().handle()
    day = today + timedelta(days=(weekday - today.weekday()) % 7)
    allowed = (weekday >= 5) == (kind == 0)
    response = db_client.post(
        BASE,
        json=payload(day) | {"type": kind, "time": period},
        headers=HEADERS,
    )
    assert response.status_code == (201 if allowed else 409), response.text
    if not allowed:
        assert (
            response.json()["content"]["error"]["code"]
            == "invalid_workday_exception_day"
        )
    records = db_client.get(BASE, headers=HEADERS).json()["content"]
    assert len(records) == int(allowed)


async def test_existing_invalid_future_exception_can_be_deleted(
    db_client: TestClient, manager: DbSessionManager
) -> None:
    async with manager.transaction() as session:
        record = WorkdayExceptionRecord(
            date=next_weekend(), type=1, time=0, title="Legacy"
        )
        session.add(record)
        await session.flush()
        entry_id = record.id
    assert db_client.delete(f"{BASE}/{entry_id}", headers=HEADERS).status_code == 204


def test_openapi_documents_exception_day_restrictions() -> None:
    schema = create_app().openapi()
    for path, method in [(BASE, "post")]:
        operation = schema["paths"][path][method]
        assert "invalid_workday_exception_day" in str(operation["responses"]["409"])
        assert "Holidays require Monday through Friday" in operation["description"]


async def test_update_is_not_available(
    db_client: TestClient, manager: DbSessionManager
) -> None:
    created = db_client.post(BASE, json=payload(), headers=HEADERS).json()["content"]
    path = f"{BASE}/{created['id']}"
    assert (
        db_client.patch(path, json={"title": "Changed"}, headers=HEADERS).status_code
        == 405
    )
    assert "patch" not in create_app().openapi()["paths"][BASE + "/{exception_id}"]


@pytest.mark.parametrize("existing_type", [0, 1])
@pytest.mark.parametrize("requested_type", [0, 1])
@pytest.mark.parametrize("existing_period", [0, 1, 2])
@pytest.mark.parametrize("requested_period", [0, 1, 2])
async def test_exception_overlap_matrix(
    db_client: TestClient,
    manager: DbSessionManager,
    existing_type: int,
    requested_type: int,
    existing_period: int,
    requested_period: int,
) -> None:
    day = next_weekday() if requested_type == 1 else next_weekend()
    async with manager.transaction() as session:
        # Direct seeding covers legacy exceptions with the opposite type.
        session.add(
            WorkdayExceptionRecord(
                date=day,
                type=existing_type,
                time=existing_period,
                title="Private existing title",
            )
        )
        session.add(
            WorkdayExceptionRecord(
                date=day + timedelta(days=7),
                type=1 - requested_type,
                time=0,
                title="Other date",
            )
        )
    before = db_client.get(BASE, headers=HEADERS).json()["content"]
    allowed = (
        existing_type == requested_type
        and existing_period != 0
        and requested_period != 0
        and existing_period != requested_period
    )
    response = db_client.post(
        BASE,
        json=payload(day) | {"type": requested_type, "time": requested_period},
        headers=HEADERS,
    )
    assert response.status_code == (201 if allowed else 409), response.text
    after = db_client.get(BASE, headers=HEADERS).json()["content"]
    if allowed:
        assert len(after) == 3
    else:
        assert (
            response.json()["content"]["error"]["code"] == "workday_exception_overlap"
        )
        assert "Private existing title" not in response.text
        assert after == before


async def test_exception_on_another_date_does_not_conflict(
    db_client: TestClient, manager: DbSessionManager
) -> None:
    assert db_client.post(BASE, json=payload(), headers=HEADERS).status_code == 201
    assert (
        db_client.post(
            BASE, json=payload(next_weekday() + timedelta(days=7)), headers=HEADERS
        ).status_code
        == 201
    )


def test_openapi_documents_overlap_rejection() -> None:
    schema = create_app().openapi()
    operation = schema["paths"][BASE]["post"]
    assert "workday_exception_overlap" in str(operation["responses"]["409"])
    assert (
        "Matching-type morning and afternoon exceptions may coexist"
        in operation["description"]
    )
    for methods in (schema["paths"][BASE], schema["paths"][BASE + "/{exception_id}"]):
        for operation in methods.values():
            assert "Overlaps are allowed" not in operation["description"]
