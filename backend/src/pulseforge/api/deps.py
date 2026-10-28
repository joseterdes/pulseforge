from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session

from pulseforge.core.auth import AuthError, AuthUnavailable, Claims
from pulseforge.core.problems import Problem

_BEARER = {"WWW-Authenticate": "Bearer"}


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session
        session.commit()


def _unauthorized() -> Problem:
    return Problem(401, "Unauthorized", headers=_BEARER)


def current_claims(request: Request) -> Claims:
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    token = token.strip()
    if scheme.lower() != "bearer" or not token:
        raise _unauthorized()
    try:
        return request.app.state.verifier.verify(token)
    except AuthError:
        raise _unauthorized() from None
    except AuthUnavailable:
        raise Problem(503, "Service Unavailable", "login service unreachable") from None
