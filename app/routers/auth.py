"""
Local authentication + self-service profile/settings. There is deliberately
no "forgot password" email flow, no OAuth, no external identity provider —
none of that works offline. Password resets when a user is fully locked out
are an admin/local-database action (see scripts/seed_admin.py), not a
self-service email flow.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Agent
from app.schemas import (
    LoginRequest,
    MeOut,
    PasswordChangeRequest,
    ProfileUpdate,
    TokenResponse,
)
from app.security import (
    create_access_token,
    get_current_agent,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

VALID_LANGUAGES = ("en", "sw")
VALID_TEMP_UNITS = ("celsius", "fahrenheit")


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.username == payload.username).first()

    if agent is None or not verify_password(payload.password, agent.password_hash):
        # Same error for "no such user" and "wrong password" — don't leak
        # which one it was.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    if not agent.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated. Contact your administrator.",
        )

    token = create_access_token(subject=agent.username, role=agent.role)
    return TokenResponse(access_token=token, role=agent.role, full_name=agent.full_name)


@router.get("/me", response_model=MeOut)
def me(agent: Agent = Depends(get_current_agent)):
    return agent


@router.patch("/me", response_model=MeOut)
def update_me(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    if payload.preferred_language is not None:
        if payload.preferred_language not in VALID_LANGUAGES:
            raise HTTPException(
                status_code=400, detail=f"preferred_language must be one of {VALID_LANGUAGES}"
            )
        agent.preferred_language = payload.preferred_language

    if payload.temperature_unit is not None:
        if payload.temperature_unit not in VALID_TEMP_UNITS:
            raise HTTPException(
                status_code=400, detail=f"temperature_unit must be one of {VALID_TEMP_UNITS}"
            )
        agent.temperature_unit = payload.temperature_unit

    if payload.full_name is not None:
        if not payload.full_name.strip():
            raise HTTPException(status_code=400, detail="full_name cannot be empty")
        agent.full_name = payload.full_name.strip()

    db.commit()
    db.refresh(agent)
    return agent


@router.post("/me/change-password")
def change_password(
    payload: PasswordChangeRequest,
    db: Session = Depends(get_db),
    agent: Agent = Depends(get_current_agent),
):
    if not verify_password(payload.current_password, agent.password_hash):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    agent.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"detail": "Password updated successfully"}
