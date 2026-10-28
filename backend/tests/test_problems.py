import pytest
from fastapi.testclient import TestClient
from pulseforge.api.app import create_app
from pulseforge.core.problems import Problem
from pulseforge.core.settings import Settings
from pydantic import BaseModel


class Echo(BaseModel):
    n: int


@pytest.fixture
def app_with_routes(settings: Settings) -> TestClient:
    app = create_app(settings)

    @app.get("/conflict")
    def conflict():
        raise Problem(409, "Conflict", "already done")

    @app.post("/echo")
    def echo(body: Echo):
        return body

    @app.get("/boom")
    def boom():
        raise RuntimeError("db password=hunter2")

    return TestClient(app, raise_server_exceptions=False)


def test_unknown_route_is_problem_json(client):
    r = client.get("/nope")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.json() == {"type": "about:blank", "title": "Not Found", "status": 404}


def test_problem_exception_renders(app_with_routes):
    r = app_with_routes.get("/conflict")
    assert r.status_code == 409 and r.json()["detail"] == "already done"


def test_validation_error_is_422_problem(app_with_routes):
    r = app_with_routes.post("/echo", json={"n": "x"})
    assert r.status_code == 422 and r.json()["title"] == "Validation Error"
    assert r.json()["errors"][0]["loc"][-1] == "n"


def test_unhandled_error_hides_details(app_with_routes):
    r = app_with_routes.get("/boom")
    assert r.status_code == 500 and "hunter2" not in r.text
    assert r.json() == {"type": "about:blank", "title": "Internal Server Error", "status": 500}
