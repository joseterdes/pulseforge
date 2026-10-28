import uuid

import jwt
import pytest
from fastapi.testclient import TestClient
from pulseforge.api.app import create_app
from pulseforge.core.auth import TokenVerifier
from pulseforge.db.models import UserProfile
from sqlalchemy import func, select


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def api(settings, verifier, migrated_db, db_session):
    with TestClient(create_app(settings, verifier=verifier)) as c:
        yield c


def _count(db_session) -> int:
    return db_session.scalar(select(func.count()).select_from(UserProfile))


def test_get_me_creates_profile_with_defaults(api, make_token):
    uid = uuid.uuid4()
    r = api.get("/v1/me", headers=auth(make_token(sub=str(uid))))
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == str(uid) and body["email"] == "dj@example.com"
    assert (body["plan"], body["ui_mode"], body["tos_version_accepted"], body["tos_current_version"]) == (
        "free",
        "simple",
        None,
        "v1",
    )


def test_get_me_is_idempotent(api, make_token, db_session):
    h = auth(make_token())
    first = api.get("/v1/me", headers=h).json()
    second = api.get("/v1/me", headers=h).json()
    assert first["created_at"] == second["created_at"]
    assert _count(db_session) == 1


def test_get_me_when_row_already_exists(api, make_token, db_session):
    uid = uuid.uuid4()
    db_session.add(UserProfile(id=uid))
    db_session.commit()
    r = api.get("/v1/me", headers=auth(make_token(sub=str(uid))))
    assert r.status_code == 200
    assert _count(db_session) == 1


@pytest.mark.parametrize("header", [None, "Basic abc", "Bearer", "Bearer ", "Bearer not.a.jwt"])
def test_me_rejects_bad_auth_headers(api, header):
    r = api.get("/v1/me", headers={"Authorization": header} if header else {})
    assert r.status_code == 401 and r.headers["content-type"].startswith("application/problem+json")
    assert r.headers["www-authenticate"] == "Bearer"


def test_me_accepts_lowercase_bearer(api, make_token):
    r = api.get("/v1/me", headers={"Authorization": f"bearer {make_token()}"})
    assert r.status_code == 200


def test_patch_me_updates_ui_mode_and_display_name(api, make_token):
    h = auth(make_token())
    r = api.patch("/v1/me", headers=h, json={"ui_mode": "pro", "display_name": "  DJ Imz  "})
    assert r.status_code == 200 and r.json()["ui_mode"] == "pro" and r.json()["display_name"] == "DJ Imz"
    assert api.get("/v1/me", headers=h).json()["ui_mode"] == "pro"


def test_patch_me_bumps_updated_at_and_keeps_unsent_fields(api, make_token, db_session):
    uid = uuid.uuid4()
    h = auth(make_token(sub=str(uid)))
    api.patch("/v1/me", headers=h, json={"display_name": "A"})
    before = db_session.scalar(select(UserProfile.updated_at).where(UserProfile.id == uid))
    r = api.patch("/v1/me", headers=h, json={"ui_mode": "pro"})
    assert r.json()["display_name"] == "A"
    db_session.expire_all()
    after = db_session.scalar(select(UserProfile.updated_at).where(UserProfile.id == uid))
    assert after > before


@pytest.mark.parametrize("payload", [{"plan": "pro"}, {"ui_mode": "PRO"}, {"display_name": ""}, {"display_name": "x" * 51}])
def test_patch_me_rejects_plan_and_bad_values(api, make_token, payload):
    h = auth(make_token())
    r = api.patch("/v1/me", headers=h, json=payload)
    assert r.status_code == 422 and r.headers["content-type"].startswith("application/problem+json")
    body = api.get("/v1/me", headers=h).json()
    assert body["plan"] == "free" and body["ui_mode"] == "simple"


def test_accept_current_tos(api, make_token):
    r = api.post("/v1/me/tos", headers=auth(make_token()), json={"version": "v1"})
    assert r.status_code == 200
    assert r.json()["tos_version_accepted"] == "v1" and r.json()["tos_accepted_at"] is not None


def test_accept_outdated_tos_conflicts(api, make_token):
    r = api.post("/v1/me/tos", headers=auth(make_token()), json={"version": "v0"})
    assert r.status_code == 409 and r.headers["content-type"].startswith("application/problem+json")


def test_me_returns_503_when_jwks_unreachable(settings, migrated_db, make_token):
    def boom(_token):
        raise jwt.PyJWKClientConnectionError("down")

    v = TokenVerifier(issuer="https://test.supabase.co/auth/v1", audience="authenticated", get_signing_key=boom)
    with TestClient(create_app(settings, verifier=v)) as c:
        r = c.get("/v1/me", headers=auth(make_token()))
    assert r.status_code == 503 and r.headers["content-type"].startswith("application/problem+json")
