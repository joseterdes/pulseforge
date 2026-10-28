from fastapi import APIRouter, Request
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from pulseforge.core.problems import Problem

router = APIRouter()


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
def readyz(request: Request) -> dict[str, str]:
    try:
        with request.app.state.session_factory() as session:
            session.execute(text("SELECT 1"))
    except OperationalError as exc:
        raise Problem(503, "Service Unavailable", "database unreachable") from exc
    return {"status": "ok"}
