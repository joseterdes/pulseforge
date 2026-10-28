from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from pulseforge.api.routers import health, me
from pulseforge.core.auth import TokenVerifier
from pulseforge.core.problems import install_problem_handlers
from pulseforge.core.settings import Settings, get_settings
from pulseforge.db.session import make_session_factory


def create_app(settings: Settings | None = None, *, verifier: TokenVerifier | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        app.state.session_factory.kw["bind"].dispose()

    app = FastAPI(title="PulseForge API", lifespan=lifespan)
    app.state.settings = settings or get_settings()
    app.state.verifier = verifier or TokenVerifier.for_supabase(app.state.settings)
    app.state.session_factory = make_session_factory(app.state.settings.database_url)
    install_problem_handlers(app)
    app.include_router(health.router)
    app.include_router(me.router)
    return app
