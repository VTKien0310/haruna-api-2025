from fastapi import FastAPI
from .core import bootstrap_application
from .http import router_registry


def create_app() -> FastAPI:
    return bootstrap_application(router_registry)
