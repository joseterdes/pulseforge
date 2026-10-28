import os
import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from pulseforge.api.app import create_app
from pulseforge.core.auth import TokenVerifier
from pulseforge.core.settings import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url=os.getenv("TEST_DATABASE_URL", "postgresql+psycopg://nobody@127.0.0.1:1/none"),
        supabase_url="https://test.supabase.co",
    )


@pytest.fixture
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))


ISSUER = "https://test.supabase.co/auth/v1"


@pytest.fixture
def private_key() -> ec.EllipticCurvePrivateKey:
    return ec.generate_private_key(ec.SECP256R1())


@pytest.fixture
def make_token(private_key):
    def _make(**overrides) -> str:
        claims = {
            "sub": str(uuid.uuid4()),
            "email": "dj@example.com",
            "aud": "authenticated",
            "iss": ISSUER,
            "role": "authenticated",
            "exp": int(time.time()) + 3600,
        }
        claims.update(overrides)
        claims = {k: v for k, v in claims.items() if v is not None}
        return jwt.encode(claims, private_key, algorithm="ES256", headers={"kid": "test-key"})

    return _make


@pytest.fixture
def verifier(private_key) -> TokenVerifier:
    return TokenVerifier(
        issuer=ISSUER,
        audience="authenticated",
        get_signing_key=lambda _token: private_key.public_key(),
    )
