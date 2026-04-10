"""Append-only audit log for ingestion (DRD §3.5 baseline)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.db.models import AuditLog


def log_audit_event(
    db: Session,
    *,
    event_type: str,
    entity_table: str,
    entity_id: int | None,
    detail: dict[str, Any] | None = None,
) -> AuditLog:
    row = AuditLog(
        event_type=(event_type or "event")[:64],
        entity_table=(entity_table or "unknown")[:64],
        entity_id=entity_id,
        detail=dict(detail or {}),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
