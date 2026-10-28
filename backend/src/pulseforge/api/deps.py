import logging
from collections.abc import Iterator
from typing import Annotated

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from pulseforge.core.auth import AuthError, AuthUnavailable, Claims
from pulseforge.core.problems import Problem

logger = logging.getLogger(__name__)

_BEARER = {"WWW-Authenticate": "Bearer"}

# Documentation only (declares the bearer scheme in OpenAPI); current_claims parses the header.
bearer_scheme = HTTPBearer(auto_error=False)


def get_session(request: Request) -> Iterator[Session]:
    """Sole transaction owner: commit on success, roll back on error."""
    with request.app.state.session_factory() as session:
        try:
            yield session
            session.commit()
        except BaseException:
            session.rollback()
            raise


# scope="function": the post-yield commit runs before the response is sent, so a
# failed commit becomes a 500 instead of a 200.
DbSession = Annotated[Session, Depends(get_session, scope="function")]


def _unauthorized() -> Problem:
    return Problem(401, "Unauthorized", headers=_BEARER)


def current_claims(request: Request) -> Claims:
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    token = token.strip()
    if scheme.lower() != "bearer" or not token:
        raise _unauthorized()
    try:
        return request.app.state.verifier.verify(token)
    except AuthError as exc:
        if isinstance(exc.__cause__, jwt.PyJWKSetError):
            logger.warning("JWKS has no usable keys (%s)", type(exc.__cause__).__name__)
        raise _unauthorized() from None
    except AuthUnavailable:
        logger.warning("Auth unavailable: signing keys could not be fetched")
        raise Problem(503, "Service Unavailable", "login service unreachable") from None
