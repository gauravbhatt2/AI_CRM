"""FastAPI dependencies (DB session, etc.)."""

from collections.abc import Generator

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_session as open_db_session


def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy Session; 503 if DATABASE_URL is missing or engine cannot start."""
    if not (settings.database_url or "").strip():
        raise HTTPException(
            status_code=503,
            detail="DATABASE_URL is not configured. Set it in the environment or .env file.",
        )
    try:
        yield from open_db_session()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail="DATABASE_URL is not configured. Set it in the environment or .env file.",
        ) from exc
