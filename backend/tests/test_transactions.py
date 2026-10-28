from fastapi.testclient import TestClient
from pulseforge.api.app import create_app
from pulseforge.api.deps import DbSession
from sqlalchemy.orm import Session, sessionmaker


class CommitFails(Session):
    def commit(self):
        raise RuntimeError("commit exploded")


def test_commit_failure_is_a_500_problem_not_a_200(settings):
    app = create_app(settings)
    app.state.session_factory = sessionmaker(bind=app.state.session_factory.kw["bind"], class_=CommitFails)

    @app.get("/txn")
    def txn(session: DbSession):
        return {"ok": True}

    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/txn")
    assert r.status_code == 500
    assert r.headers["content-type"].startswith("application/problem+json")
    assert "exploded" not in r.text
