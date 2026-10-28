from typing import TYPE_CHECKING

from fastapi import FastAPI

from pulseforge.api.routers import health
from pulseforge.core.settings import Settings, get_settings

if TYPE_CHECKING:  # TokenVerifier arrives in Task 3
    from pulseforge.api.auth import TokenVerifier


def create_app(settings: Settings | None = None, *, verifier: "TokenVerifier | None" = None) -> FastAPI:
    app = FastAPI(title="PulseForge API")
    app.state.settings = settings or get_settings()
    app.state.verifier = verifier
    app.include_router(health.router)
    return app
