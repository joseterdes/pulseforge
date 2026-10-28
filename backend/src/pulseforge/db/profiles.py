import uuid

from sqlalchemy import select
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from pulseforge.db.models import UserProfile


def get_or_create_profile(session: Session, user_id: uuid.UUID) -> UserProfile:
    """Race-safe: concurrent first requests both succeed and leave one row."""
    session.execute(postgresql.insert(UserProfile).values(id=user_id).on_conflict_do_nothing(index_elements=["id"]))
    return session.execute(select(UserProfile).where(UserProfile.id == user_id)).scalar_one()
