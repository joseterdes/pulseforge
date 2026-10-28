"""users_profile

Revision ID: 0001
Revises:
Create Date: 2026-10-28
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users_profile",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, autoincrement=False),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("plan", sa.Text(), nullable=False, server_default=sa.text("'free'")),
        sa.Column("ui_mode", sa.Text(), nullable=False, server_default=sa.text("'simple'")),
        sa.Column("tos_version_accepted", sa.Text(), nullable=True),
        sa.Column("tos_accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("plan IN ('free','creator','pro')", name="users_profile_plan_check"),
        sa.CheckConstraint("ui_mode IN ('simple','pro')", name="users_profile_ui_mode_check"),
    )


def downgrade() -> None:
    op.drop_table("users_profile")
