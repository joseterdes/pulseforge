import os
import time
import uuid

import jwt
import pytest
from alembic import command
from alembic.config import Config
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from pulseforge.api.app import create_app
from pulseforge.core.auth import TokenVerifier
from pulseforge.core.settings import Settings
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


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


@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        if os.getenv("CI"):
            pytest.fail("TEST_DATABASE_URL must be set in CI; DB tests may not be skipped")
        pytest.skip("TEST_DATABASE_URL not set")
    return url


@pytest.fixture(scope="session")
def alembic_cfg(database_url: str) -> Config:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


@pytest.fixture(scope="session")
def migrated_db(database_url: str, alembic_cfg: Config) -> str:
    command.upgrade(alembic_cfg, "head")
    return database_url


@pytest.fixture
def db_session(migrated_db: str):
    engine = create_engine(migrated_db)
    with Session(engine) as session:
        yield session
        session.rollback()
        session.execute(text("TRUNCATE users_profile"))
        session.commit()
    engine.dispose()
