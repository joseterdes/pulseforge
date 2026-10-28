import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UserProfile(Base):
    __tablename__ = "users_profile"
    __table_args__ = (
        CheckConstraint("plan IN ('free','creator','pro')", name="users_profile_plan_check"),
        CheckConstraint("ui_mode IN ('simple','pro')", name="users_profile_ui_mode_check"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, autoincrement=False)
    display_name: Mapped[str | None] = mapped_column(Text)
    plan: Mapped[str] = mapped_column(Text, server_default=text("'free'"))
    ui_mode: Mapped[str] = mapped_column(Text, server_default=text("'simple'"))
    tos_version_accepted: Mapped[str | None] = mapped_column(Text)
    tos_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
