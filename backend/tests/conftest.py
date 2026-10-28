import os

import pytest
from fastapi.testclient import TestClient
from pulseforge.api.app import create_app
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
