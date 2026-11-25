import logging
from typing import Annotated

from fastapi import Depends

from app.core import logger_dependency

AttendanceLoggerDep = Annotated[
    logging.Logger, Depends(logger_dependency("attendance"))
]
