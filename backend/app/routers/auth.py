"""
Local authentication. There is deliberately no "forgot password" email flow,
no OAuth, no external identity provider — none of that works offline.
Password resets are an admin/local-database action (TODO: build a small
admin CLI or endpoint for this rather than a self-service email flow).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Agent
from app.schemas import LoginRequest, TokenResponse
from app.security import create_access_token, get_current_agent, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


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


@router.get("/me")
def me(agent: Agent = Depends(get_current_agent)):
    return {
        "username": agent.username,
        "full_name": agent.full_name,
        "role": agent.role,
    }
