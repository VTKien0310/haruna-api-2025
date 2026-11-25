import logging
import re

import pytest

from app import create_app
from app.core import apply_log_level_for_application, get_logger, log_startup, settings

_LINE = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z INFO app\.request request method=GET "
    r"path=/health status=200"
)


def _stderr_handlers() -> list[logging.Handler]:
    return [
        handler
        for handler in logging.getLogger("app").handlers
        if handler.name == "app.stderr"
    ]


def test_apply_log_level_for_application_is_idempotent() -> None:
    apply_log_level_for_application("DEBUG")
    apply_log_level_for_application("WARNING")
    create_app()

    logger = logging.getLogger("app")
    assert logger.propagate is False
    assert logger.level == logging.INFO
    assert len(_stderr_handlers()) == 1

    apply_log_level_for_application("DEBUG")
    apply_log_level_for_application("DEBUG")
    assert logger.level == logging.DEBUG
    assert len(_stderr_handlers()) == 1
    apply_log_level_for_application("INFO")


def test_app_request_and_auth_emit_info_records(
    caplog: pytest.LogCaptureFixture,
) -> None:
    apply_log_level_for_application("INFO")
    get_logger("request").info(
        "request method=GET path=/health status=200 duration_ms=1.0"
    )
    get_logger("auth").info(
        "access token authenticated path=local alg=ES256 kid=test-kid iss=issuer"
    )

    emitted = {(record.name, record.levelno) for record in caplog.records}
    assert ("app.request", logging.INFO) in emitted
    assert ("app.auth", logging.INFO) in emitted
    assert any("path=/health" in message for message in caplog.messages)
    assert any("alg=ES256" in message for message in caplog.messages)
    assert any("kid=test-kid" in message for message in caplog.messages)
    assert any("iss=issuer" in message for message in caplog.messages)


def test_log_line_has_timestamp_level_name_and_message(
    caplog: pytest.LogCaptureFixture,
) -> None:
    apply_log_level_for_application("INFO")
    get_logger("request").info("request method=GET path=/health status=200")
    record = next(record for record in caplog.records if record.name == "app.request")
    rendered = _stderr_handlers()[0].format(record)
    assert _LINE.fullmatch(rendered)


def test_records_do_not_propagate_to_the_root_logger(
    caplog: pytest.LogCaptureFixture,
) -> None:
    apply_log_level_for_application("INFO")
    root_records: list[logging.LogRecord] = []

    class _RootProbe(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            root_records.append(record)

    probe = _RootProbe()
    logging.getLogger().addHandler(probe)
    try:
        get_logger("auth").info("access token authenticated path=local")
    finally:
        logging.getLogger().removeHandler(probe)

    assert root_records == []
    assert any(record.name == "app.auth" for record in caplog.records)


def test_warning_level_hides_info_records(caplog: pytest.LogCaptureFixture) -> None:
    apply_log_level_for_application("WARNING")
    try:
        get_logger("request").info("hidden-info-marker")
        get_logger("request").warning("shown-warning-marker")
    finally:
        apply_log_level_for_application("INFO")

    messages = " ".join(caplog.messages)
    assert "hidden-info-marker" not in messages
    assert "shown-warning-marker" in messages


def test_invalid_log_level_uses_info(caplog: pytest.LogCaptureFixture) -> None:
    apply_log_level_for_application("not-a-level")
    try:
        assert logging.getLogger("app").level == logging.INFO
        assert "invalid LOG_LEVEL; using INFO" in caplog.messages
    finally:
        apply_log_level_for_application("INFO")


def test_startup_log_omits_secret_values(caplog: pytest.LogCaptureFixture) -> None:
    apply_log_level_for_application("INFO")
    log_startup()
    rendered = _stderr_handlers()[0].format(
        next(record for record in caplog.records if "startup " in record.getMessage())
    )

    assert "environment=testing" in rendered
    assert "log_level=INFO" in rendered
    assert "supabase_host=supabase.invalid" in rendered
    assert "ai_host=ai.invalid" in rendered
    assert settings.DB_PASSWORD not in rendered
    assert settings.SUPABASE_SERVICE_ROLE_KEY not in rendered
    assert settings.AI_API_KEY not in rendered
    assert "[redacted]" not in rendered


def test_handler_redacts_secrets_and_bearer_tokens(
    caplog: pytest.LogCaptureFixture,
) -> None:
    apply_log_level_for_application("INFO")
    get_logger("core").info(
        "db=%s key=%s ai=%s Authorization=Bearer %s",
        settings.DB_PASSWORD,
        settings.SUPABASE_SERVICE_ROLE_KEY,
        settings.AI_API_KEY,
        "another-access-token",
    )
    rendered = _stderr_handlers()[0].format(
        next(record for record in caplog.records if record.name == "app.core")
    )

    assert settings.DB_PASSWORD not in rendered
    assert settings.SUPABASE_SERVICE_ROLE_KEY not in rendered
    assert settings.AI_API_KEY not in rendered
    assert "another-access-token" not in rendered
    assert "Bearer [redacted]" in rendered
    assert "[redacted]" in caplog.messages[-1]
