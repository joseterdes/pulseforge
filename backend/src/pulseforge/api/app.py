from typing import TYPE_CHECKING

from fastapi import FastAPI

from pulseforge.api.routers import health
from pulseforge.core.problems import install_problem_handlers
from pulseforge.core.settings import Settings, get_settings

if TYPE_CHECKING:  # TokenVerifier arrives in Task 3
    from pulseforge.core.auth import TokenVerifier


def create_app(settings: Settings | None = None, *, verifier: "TokenVerifier | None" = None) -> FastAPI:
    app = FastAPI(title="PulseForge API")
    app.state.settings = settings or get_settings()
    app.state.verifier = verifier
    install_problem_handlers(app)
    app.include_router(health.router)
    return app
