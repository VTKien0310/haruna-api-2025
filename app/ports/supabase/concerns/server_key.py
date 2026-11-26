def is_legacy_jwt_api_key(api_key: str) -> bool:
    """A legacy anon or service_role key is a JWT: three non-empty segments."""
    parts = api_key.strip().split(".")
    return len(parts) == 3 and all(parts)


def headers_for_server_key(api_key: str) -> dict[str, str]:
    """Headers that identify this API process to Supabase.

    A secret or publishable key (`sb_secret_`, `sb_publishable_`) is not a JWT,
    so it is sent only as `apikey`. A legacy JWT key is also sent as
    `Authorization: Bearer`.
    """
    stripped = api_key.strip()
    if not stripped:
        return {}
    headers = {"apikey": stripped}
    if is_legacy_jwt_api_key(stripped):
        headers["Authorization"] = f"Bearer {stripped}"
    return headers


def drop_non_jwt_bearer(headers: object, api_key: str) -> None:
    """Remove `Authorization: Bearer <api_key>` when the key is not a JWT."""
    if is_legacy_jwt_api_key(api_key) or not isinstance(headers, dict):
        return
    bearer = f"Bearer {api_key.strip()}"
    for key in [key for key in headers if str(key).lower() == "authorization"]:
        if headers[key] == bearer:
            del headers[key]
