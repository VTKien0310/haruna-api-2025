import logging
from typing import Annotated

from fastapi import Depends

from app.core import logger_dependency

ProfileLoggerDep = Annotated[logging.Logger, Depends(logger_dependency("profile"))]
