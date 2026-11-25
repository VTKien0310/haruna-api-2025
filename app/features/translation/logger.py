import logging
from typing import Annotated

from fastapi import Depends

from app.core import logger_dependency

TranslationLoggerDep = Annotated[
    logging.Logger, Depends(logger_dependency("translation"))
]
