"""
Delete all rows from crm_records. Requires DATABASE_URL (same as the API).

Usage (from ai-crm-system directory):
  python -m scripts.clear_crm_records
"""

from sqlalchemy import delete

from app.db.database import init_engine, init_db
from app.db.models import CrmRecord


def main() -> None:
    init_engine()
    init_db()
    from app.db.database import get_engine

    engine = get_engine()
    if engine is None:
        raise SystemExit("DATABASE_URL is not set; cannot connect.")

    with engine.begin() as conn:
        result = conn.execute(delete(CrmRecord))
        n = result.rowcount if result.rowcount is not None else 0
    print(f"Deleted {n} row(s) from crm_records.")


if __name__ == "__main__":
    main()
