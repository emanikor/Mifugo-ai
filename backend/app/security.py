"""
JWT + password hashing utilities shared across routers.

Token-based (not session-cookie) auth because the frontend is a decoupled
SPA served from a different port (5173) than the API (8000) — this is
simplest and most standard for that shape, and still works entirely
offline since verification is local (HMAC secret), no external identity
provider involved.
"""
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Agent

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# tokenUrl points at the login endpoint for OpenAPI docs purposes only —
# the frontend calls it directly, this doesn't route anywhere itself.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def create_access_token(*, subject: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def get_current_agent(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Agent:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_error
    except JWTError:
        raise credentials_error

    agent = db.query(Agent).filter(Agent.username == username).first()
    if agent is None or not agent.is_active:
        raise credentials_error
    return agent


def require_role(*allowed_roles: str):
    """Dependency factory — e.g. Depends(require_role('official', 'admin'))"""

    def _check(agent: Agent = Depends(get_current_agent)) -> Agent:
        if agent.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(allowed_roles)}",
            )
        return agent

    return _check
