"""
SQLAlchemy engine/session setup.

pool_pre_ping matters here more than it would on a cloud deploy: on a field
laptop, Postgres inside Docker might be slow to come up, or the machine
might have been asleep/suspended. We want stale connections detected and
recycled rather than the app just throwing opaque errors.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency — one session per request, always closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
