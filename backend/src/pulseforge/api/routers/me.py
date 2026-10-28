import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func

from pulseforge.api.deps import DbSession, bearer_scheme, current_claims
from pulseforge.api.types import plain_text
from pulseforge.core.auth import Claims
from pulseforge.core.problems import Problem
from pulseforge.db.models import UserProfile
from pulseforge.db.profiles import get_or_create_profile

router = APIRouter(prefix="/v1/me", tags=["me"], dependencies=[Depends(bearer_scheme)])

UiMode = Literal["simple", "pro"]
CurrentClaims = Annotated[Claims, Depends(current_claims)]


class MeOut(BaseModel):
    id: uuid.UUID
    email: str | None
    display_name: str | None
    plan: str
    ui_mode: UiMode
    tos_version_accepted: str | None
    tos_accepted_at: datetime | None
    tos_current_version: str
    created_at: datetime


class MePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: plain_text(1, 50) | None = None
    ui_mode: UiMode | None = None


class TosAccept(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str


def _out(profile: UserProfile, claims: Claims, request: Request) -> MeOut:
    return MeOut(
        id=profile.id,
        email=claims.email,
        display_name=profile.display_name,
        plan=profile.plan,
        ui_mode=profile.ui_mode,  # type: ignore[arg-type]  # DB check constraint guarantees the literal
        tos_version_accepted=profile.tos_version_accepted,
        tos_accepted_at=profile.tos_accepted_at,
        tos_current_version=request.app.state.settings.tos_version,
        created_at=profile.created_at,
    )


@router.get("", response_model=MeOut)
def get_me(
    request: Request,
    claims: CurrentClaims,
    session: DbSession,
) -> MeOut:
    profile = get_or_create_profile(session, claims.sub)
    return _out(profile, claims, request)


@router.patch("", response_model=MeOut)
def patch_me(
    body: MePatch,
    request: Request,
    claims: CurrentClaims,
    session: DbSession,
) -> MeOut:
    profile = get_or_create_profile(session, claims.sub)
    changes = body.model_dump(exclude_none=True)
    for field, value in changes.items():
        setattr(profile, field, value)
    if changes:
        profile.updated_at = func.now()  # type: ignore[assignment]  # SQL expression, no ORM onupdate
    session.flush()
    session.refresh(profile)
    return _out(profile, claims, request)


@router.post("/tos", response_model=MeOut)
def accept_tos(
    body: TosAccept,
    request: Request,
    claims: CurrentClaims,
    session: DbSession,
) -> MeOut:
    if body.version != request.app.state.settings.tos_version:
        raise Problem(409, "Conflict", "ToS version is not current")
    profile = get_or_create_profile(session, claims.sub)
    profile.tos_version_accepted = body.version
    profile.tos_accepted_at = func.now()  # type: ignore[assignment]
    profile.updated_at = func.now()  # type: ignore[assignment]
    session.flush()
    session.refresh(profile)
    return _out(profile, claims, request)
