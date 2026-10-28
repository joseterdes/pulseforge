from fastapi.testclient import TestClient
from pulseforge.api.app import create_app


def test_readyz_ok_with_database(migrated_db, settings):
    with TestClient(create_app(settings)) as c:
        r = c.get("/readyz")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_readyz_503_when_database_unreachable(settings):
    bad = settings.model_copy(update={"database_url": "postgresql+psycopg://nobody@127.0.0.1:1/none"})
    with TestClient(create_app(bad)) as c:
        r = c.get("/readyz")
    assert r.status_code == 503 and r.headers["content-type"].startswith("application/problem+json")
