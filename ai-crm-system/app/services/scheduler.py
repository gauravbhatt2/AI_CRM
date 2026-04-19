"""
Background jobs (APScheduler) — scheduled follow-up emails after ingestion.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None

_EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


def _resolve_followup_to(row: Any) -> str:
    for p in list(row.participants or []):
        m = _EMAIL_RE.search(str(p))
        if m:
            return m.group(0)
    meta = row.source_metadata if isinstance(row.source_metadata, dict) else {}
    for key in ("contact_email", "email", "to", "recipient", "customer_email"):
        v = meta.get(key)
        if isinstance(v, str):
            m = _EMAIL_RE.search(v)
            if m:
                return m.group(0)
    for s in list(row.stakeholders or []):
        m = _EMAIL_RE.search(str(s))
        if m:
            return m.group(0)
    fb = (settings.followup_default_email or "").strip()
    if fb and _EMAIL_RE.search(fb):
        return _EMAIL_RE.search(fb).group(0)
    return "demo-recipient@example.com"


def _execute_scheduled_followup(record_id: int) -> None:
    """Runs in worker thread: load record, draft email, send via gmail_service."""
    from app.db.database import SessionLocal, init_engine
    from app.db.models import CrmRecord
    from app.agents.tools import crm_row_to_agent_record
    from app.agents.followup_agent import generate_followup_email
    from app.integrations.gmail_service import send_email

    init_engine()
    if SessionLocal is None:
        logger.warning("Scheduled follow-up #%s skipped: database not configured", record_id)
        return

    db = SessionLocal()
    try:
        row = db.get(CrmRecord, record_id)
        if row is None:
            logger.info("Scheduled follow-up #%s skipped: record deleted", record_id)
            return
        rec = crm_row_to_agent_record(row)
        body = generate_followup_email(rec)
        company = str(rec.get("mentioned_company") or "").strip()
        product = str(rec.get("product") or "").strip()
        tail = company or product or f"record {record_id}"
        subject = f"Follow-up: {tail}"[:200]
        to_addr = _resolve_followup_to(row)
        send_email(to_addr, subject, body)
        logger.info("Scheduled follow-up sent for record_id=%s to=%s", record_id, to_addr)
    except Exception:
        logger.exception("Scheduled follow-up failed for record_id=%s", record_id)
    finally:
        db.close()


def start_scheduler() -> None:
    """Start global background scheduler (no-op if already running)."""
    global _scheduler
    if _scheduler is not None:
        return
    if not (settings.database_url or "").strip():
        logger.info("APScheduler not started: DATABASE_URL unset")
        return
    _scheduler = BackgroundScheduler(timezone=timezone.utc)
    _scheduler.start()
    logger.info("APScheduler started (UTC)")


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return
    try:
        _scheduler.shutdown(wait=False)
    except Exception:
        logger.exception("APScheduler shutdown error")
    _scheduler = None


def schedule_followup(record_id: int, delay_minutes: int) -> str | None:
    """
    After ``delay_minutes``, load the CRM row, generate a follow-up email, and send it.

    Returns APScheduler job id, or None if scheduling is unavailable.
    """
    if delay_minutes < 1:
        delay_minutes = 1

    if _scheduler is None:
        logger.warning("schedule_followup(%s): scheduler not running", record_id)
        return None

    run_at = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
    job_id = f"followup_{record_id}_{uuid.uuid4().hex[:10]}"
    _scheduler.add_job(
        _execute_scheduled_followup,
        trigger="date",
        run_date=run_at,
        args=[record_id],
        id=job_id,
        replace_existing=False,
    )
    logger.info(
        "Scheduled follow-up job %s for record_id=%s at %s (in %s min)",
        job_id,
        record_id,
        run_at.isoformat(),
        delay_minutes,
    )
    return job_id
