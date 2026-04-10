"""
PostgreSQL connection: SQLAlchemy engine, session factory, and table creation.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

_engine: Engine | None = None
SessionLocal: sessionmaker[Session] | None = None


def init_engine() -> None:
    """Create engine and session factory when DATABASE_URL is set."""
    global _engine, SessionLocal
    url = (settings.database_url or "").strip()
    if not url or _engine is not None:
        return
    _engine = create_engine(
        url,
        pool_pre_ping=True,
        echo=settings.debug,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def get_engine() -> Engine | None:
    """Return the SQLAlchemy engine, or None if DATABASE_URL is not configured."""
    init_engine()
    return _engine


def get_session() -> Generator[Session, None, None]:
    """
    Yield a transactional Session. Caller must ensure DATABASE_URL is set.

    Raises RuntimeError if the session factory is unavailable.
    """
    init_engine()
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL is not configured")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _ensure_crm_records_fk_columns(engine: Engine) -> None:
    """
    Add account_id / contact_id / deal_id to legacy crm_records tables.

    `metadata.create_all()` creates new tables but does not ALTER existing ones;
    older deployments may be missing these columns.
    """
    from sqlalchemy import text

    # PostgreSQL: IF NOT EXISTS keeps this idempotent.
    statements = (
        """
        ALTER TABLE crm_records
        ADD COLUMN IF NOT EXISTS account_id INTEGER
        REFERENCES accounts(id) ON DELETE SET NULL
        """,
        """
        ALTER TABLE crm_records
        ADD COLUMN IF NOT EXISTS contact_id INTEGER
        REFERENCES contacts(id) ON DELETE SET NULL
        """,
        """
        ALTER TABLE crm_records
        ADD COLUMN IF NOT EXISTS deal_id INTEGER
        REFERENCES deals(id) ON DELETE SET NULL
        """,
    )
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


def _ensure_crm_records_extended_columns(engine: Engine) -> None:
    """Add industry, custom_fields, source_*, structured_transcript, mapping_method if missing."""
    from sqlalchemy import text

    statements = (
        """
        ALTER TABLE crm_records
        ADD COLUMN IF NOT EXISTS industry VARCHAR(1024) NOT NULL DEFAULT ''
        """,
        """
        ALTER TABLE crm_records
        ADD COLUMN IF NOT EXISTS custom_fields JSONB NOT NULL DEFAULT '{}'::jsonb
        """,
        """
        ALTER TABLE crm_records
        ADD COLUMN IF NOT EXISTS source_type VARCHAR(64) NOT NULL DEFAULT 'call'
        """,
        """
        ALTER TABLE crm_records
        ADD COLUMN IF NOT EXISTS source_metadata JSONB NOT NULL DEFAULT '{}'::jsonb
        """,
        """
        ALTER TABLE crm_records
        ADD COLUMN IF NOT EXISTS structured_transcript JSONB
        """,
        """
        ALTER TABLE crm_records
        ADD COLUMN IF NOT EXISTS mapping_method VARCHAR(32) NOT NULL DEFAULT 'rules'
        """,
    )
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


def init_db() -> None:
    """Create all tables defined on Base (idempotent) and align legacy schema."""
    init_engine()
    if _engine is None:
        return
    # Import ORM modules so metadata registers all tables
    from app.db import models as _models  # noqa: F401

    _models.Base.metadata.create_all(bind=_engine)
    _ensure_crm_records_fk_columns(_engine)
    _ensure_crm_records_extended_columns(_engine)
