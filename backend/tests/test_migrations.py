import uuid

import pytest
import sqlalchemy.exc
from alembic import command
from sqlalchemy import create_engine, inspect, text


def test_migration_creates_users_profile_with_defaults(migrated_db, db_session):
    uid = uuid.uuid4()
    db_session.execute(text("INSERT INTO users_profile (id) VALUES (:id)"), {"id": uid})
    row = db_session.execute(
        text("SELECT plan, ui_mode, created_at FROM users_profile WHERE id=:id"), {"id": uid}
    ).one()
    assert (row.plan, row.ui_mode) == ("free", "simple") and row.created_at is not None


def test_ui_mode_check_constraint(migrated_db, db_session):
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        db_session.execute(
            text("INSERT INTO users_profile (id, ui_mode) VALUES (:id, 'PRO')"), {"id": uuid.uuid4()}
        )


def test_plan_check_constraint(migrated_db, db_session):
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        db_session.execute(
            text("INSERT INTO users_profile (id, plan) VALUES (:id, 'enterprise')"), {"id": uuid.uuid4()}
        )


def test_downgrade_then_upgrade_roundtrip(database_url, alembic_cfg):
    cfg = alembic_cfg
    engine = create_engine(database_url)
    try:
        command.downgrade(cfg, "base")
        assert "users_profile" not in inspect(engine).get_table_names()
        command.upgrade(cfg, "head")
        assert "users_profile" in inspect(engine).get_table_names()
    finally:
        engine.dispose()
