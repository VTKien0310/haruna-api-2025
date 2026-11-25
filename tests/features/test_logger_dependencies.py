import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.features.attendance.logger import AttendanceLoggerDep
from app.features.authentication.logger import AuthenticationLoggerDep
from app.features.authorization.logger import AuthorizationLoggerDep
from app.features.media.logger import MediaLoggerDep
from app.features.profile.logger import ProfileLoggerDep
from app.features.pto.logger import PtoLoggerDep
from app.features.translation.logger import TranslationLoggerDep


@pytest.mark.parametrize(
    ("logger_dependency_type", "expected_name"),
    [
        (AttendanceLoggerDep, "app.attendance"),
        (AuthenticationLoggerDep, "app.auth"),
        (AuthorizationLoggerDep, "app.authorization"),
        (MediaLoggerDep, "app.media"),
        (ProfileLoggerDep, "app.profile"),
        (PtoLoggerDep, "app.pto"),
        (TranslationLoggerDep, "app.translation"),
    ],
)
def test_feature_logger_dependency_resolves_expected_logger(
    logger_dependency_type: object, expected_name: str
) -> None:
    app = FastAPI()

    def read_logger(logger: logging.Logger) -> dict[str, str]:
        return {"name": logger.name}

    read_logger.__annotations__["logger"] = logger_dependency_type
    app.get("/logger")(read_logger)

    with TestClient(app) as client:
        response = client.get("/logger")

    assert response.status_code == 200
    assert response.json() == {"name": expected_name}
