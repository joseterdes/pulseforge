"""Local verification of Supabase login JWTs against the project's JWKS."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import jwt

from pulseforge.core.settings import Settings

# Fixed allow-list: never derived from the (attacker-controlled) token header.
ALGORITHMS = ["ES256", "RS256"]
LEEWAY_SECONDS = 30

SigningKeyGetter = Callable[[str], Any]


@dataclass(frozen=True)
class Claims:
    sub: uuid.UUID
    email: str | None


class AuthError(Exception):
    """The token is missing, malformed, or invalid (maps to 401)."""


class AuthUnavailable(Exception):
    """The signing keys could not be fetched (maps to 503)."""


def _jwks_getter(client: jwt.PyJWKClient) -> SigningKeyGetter:
    """Return the PyJWK itself so PyJWT enforces the key's algorithm binding.

    Fetch problems that are not PyJWT errors (non-JSON body, connection reset)
    mean the JWKS is unavailable (503); a bad token's PyJWTError stays a 401.
    """

    def get(token: str) -> Any:
        try:
            return client.get_signing_key_from_jwt(token)
        except jwt.PyJWTError:
            raise
        except (ValueError, OSError) as exc:
            raise AuthUnavailable("signing keys unavailable") from exc

    return get


class TokenVerifier:
    def __init__(self, *, issuer: str, audience: str, get_signing_key: SigningKeyGetter) -> None:
        self._issuer = issuer
        self._audience = audience
        self._get_signing_key = get_signing_key

    @classmethod
    def for_supabase(cls, settings: Settings) -> TokenVerifier:
        client = jwt.PyJWKClient(settings.jwks_url, cache_keys=True, lifespan=3600)
        return cls(
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            get_signing_key=_jwks_getter(client),
        )

    def verify(self, token: str) -> Claims:
        try:
            key = self._get_signing_key(token)
        except jwt.PyJWKClientConnectionError as exc:  # subclass: must come first
            raise AuthUnavailable("signing keys unavailable") from exc
        except jwt.PyJWTError as exc:  # includes PyJWKClientError, DecodeError
            raise AuthError("invalid token") from exc

        try:
            payload = jwt.decode(
                token,
                key,
                algorithms=ALGORITHMS,
                audience=self._audience,
                issuer=self._issuer,
                leeway=LEEWAY_SECONDS,
                options={"require": ["exp", "sub", "aud", "iss"]},
            )
            sub = uuid.UUID(str(payload["sub"]))
        except (jwt.PyJWTError, ValueError) as exc:
            raise AuthError("invalid token") from exc

        email = payload.get("email")
        return Claims(sub=sub, email=email if isinstance(email, str) else None)
