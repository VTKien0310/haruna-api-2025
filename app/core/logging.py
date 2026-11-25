import logging
import re
import sys
import time
import traceback
from collections.abc import Callable
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import Depends

from .config import settings

_LOGGER_NAME = "app"
_HANDLER_NAME = "app.stderr"
_MIN_SECRET_LENGTH = 8
_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
_LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}
_BEARER = re.compile(r"(?i)\bBearer\s+\S+")
_reported_invalid_level: str | None = None
_logger_providers: dict[str, Callable[[], logging.Logger]] = {}


class _AppFormatter(logging.Formatter):
    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)) + "Z"

    def format(self, record: logging.LogRecord) -> str:
        rendered = super().format(record)
        try:
            return _redact(rendered)
        except Exception:
            return rendered


class _RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.msg = _redact(record.getMessage())
            record.args = ()
            if record.exc_info and not record.exc_text:
                exc = record.exc_info[1]
                if isinstance(exc, BaseException):
                    record.exc_text = _redact("".join(traceback.format_exception(exc)))
            elif isinstance(record.exc_text, str):
                record.exc_text = _redact(record.exc_text)
        except Exception:
            return True
        return True


def configure_logging(level: str | None = None) -> None:
    """Attach one stderr handler to the ``app`` logger.

    Safe to call again: a second call updates the level and does not add
    another handler. Child loggers propagate here and stop, so a root or
    uvicorn handler does not print the same line.
    """
    global _reported_invalid_level
    raw = settings.LOG_LEVEL if level is None else level
    resolved, invalid = _resolve_level(raw)
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(resolved)
    logger.propagate = False

    owned = _owned_handlers(logger)
    if not owned:
        handler = logging.StreamHandler(sys.stderr)
        handler.name = _HANDLER_NAME
        handler.setFormatter(_AppFormatter(_FORMAT))
        handler.addFilter(_RedactingFilter())
        logger.addHandler(handler)
        owned = [handler]
    for extra in owned[1:]:
        logger.removeHandler(extra)

    if invalid and _reported_invalid_level != raw:
        _reported_invalid_level = raw
        logger.warning("invalid LOG_LEVEL; using INFO")


def get_logger(name: str) -> logging.Logger:
    """Return a logger under ``app``.

    ``get_logger("auth")`` and ``get_logger("app.auth")`` are both ``app.auth``.
    """
    return logging.getLogger(_qualified_logger_name(name))


def logger_dependency(name: str) -> Callable[[], logging.Logger]:
    """Return the stable FastAPI dependency callable for ``app.<name>``.

    Tests override this callable with ``app.dependency_overrides``.
    """
    qualified = _qualified_logger_name(name)
    provider = _logger_providers.get(qualified)
    if provider is not None:
        return provider

    def provide(logger_name: str = qualified) -> logging.Logger:
        return get_logger(logger_name)

    suffix = qualified.removeprefix(f"{_LOGGER_NAME}.").replace(".", "_")
    provide.__name__ = f"get_{suffix or _LOGGER_NAME}_logger"
    provide.__qualname__ = provide.__name__
    _logger_providers[qualified] = provide
    return provide


def get_logger_dep(name: str) -> Annotated[logging.Logger, Depends]:
    """Return an annotation that injects the named ``app`` logger."""
    return Annotated[logging.Logger, Depends(logger_dependency(name))]


def _qualified_logger_name(name: str) -> str:
    cleaned = name.strip().strip(".")
    if not cleaned or cleaned == _LOGGER_NAME:
        return _LOGGER_NAME
    if cleaned.startswith(f"{_LOGGER_NAME}."):
        return cleaned
    return f"{_LOGGER_NAME}.{cleaned}"


_logger = get_logger("core")


def log_startup() -> None:
    """Log the process configuration without secret values."""
    _logger.info(
        "startup environment=%s name=%s version=%s port=%s docs=%s "
        "api_prefix=%s log_level=%s db_host=%s db_port=%s db_name=%s "
        "db_schema=%s db_user_set=%s db_password_set=%s supabase_host=%s "
        "supabase_key_set=%s ai_host=%s ai_key_set=%s ai_model=%s",
        settings.ENVIRONMENT,
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.APP_PORT,
        settings.APP_ENABLE_DOCS,
        settings.API_PREFIX,
        logging.getLevelName(logging.getLogger(_LOGGER_NAME).level),
        settings.DB_HOST,
        settings.DB_PORT,
        settings.DB_NAME,
        settings.DB_SCHEMA,
        bool(settings.DB_USER),
        bool(settings.DB_PASSWORD),
        _url_host(settings.SUPABASE_URL),
        bool(settings.SUPABASE_SERVICE_ROLE_KEY),
        _url_host(settings.AI_API_ENDPOINT),
        bool(settings.AI_API_KEY),
        settings.AI_TRANSLATION_MODEL,
    )


def _owned_handlers(logger: logging.Logger) -> list[logging.Handler]:
    return [handler for handler in logger.handlers if handler.name == _HANDLER_NAME]


def _resolve_level(raw: str) -> tuple[int, bool]:
    resolved = _LEVELS.get(raw.strip().upper())
    if resolved is None:
        return logging.INFO, True
    return resolved, False


def _url_host(url: str) -> str:
    stripped = url.strip()
    if not stripped:
        return ""
    return urlsplit(stripped).hostname or ""


def _secret_values() -> list[str]:
    values = [
        settings.DB_PASSWORD,
        settings.SUPABASE_SERVICE_ROLE_KEY,
        settings.AI_API_KEY,
    ]
    secrets: list[str] = []
    for value in values:
        if len(value) >= _MIN_SECRET_LENGTH and value not in secrets:
            secrets.append(value)
    secrets.sort(key=len, reverse=True)
    return secrets


def _redact(text: str) -> str:
    redacted = text
    for secret in _secret_values():
        redacted = redacted.replace(secret, "[redacted]")
    return _BEARER.sub("Bearer [redacted]", redacted)


configure_logging()
