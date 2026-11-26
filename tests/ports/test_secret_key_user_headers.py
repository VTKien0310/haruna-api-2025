import httpx
from supabase_auth import SyncGoTrueClient

from app.ports.supabase.concerns import headers_for_server_key

_SECRET = "sb_secret_test_key_value"
_USER_TOKEN = "header.payload.signature"


def _user_response() -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "user-1",
            "aud": "authenticated",
            "role": "authenticated",
            "email": "user@example.com",
            "created_at": "2020-01-01T00:00:00Z",
            "app_metadata": {},
            "user_metadata": {},
        },
    )


def _get_user(headers: dict[str, str]) -> httpx.Request:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return _user_response()

    auth = SyncGoTrueClient(
        url="http://supabase.invalid/auth/v1",
        headers=headers,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        auto_refresh_token=False,
    )
    auth.get_user(_USER_TOKEN)
    assert len(calls) == 1
    return calls[0]


def test_get_user_sends_the_access_token_and_the_secret_key_as_apikey() -> None:
    request = _get_user(headers_for_server_key(_SECRET))

    assert request.headers["authorization"] == f"Bearer {_USER_TOKEN}"
    assert request.headers["apikey"] == _SECRET
    assert _SECRET not in request.headers["authorization"]


def test_get_user_replaces_a_bearer_secret_key_with_the_access_token() -> None:
    request = _get_user(
        {
            "apikey": _SECRET,
            "Authorization": f"Bearer {_SECRET}",
        }
    )

    assert request.headers["authorization"] == f"Bearer {_USER_TOKEN}"
    assert request.headers["apikey"] == _SECRET
    assert _SECRET not in request.headers["authorization"]
