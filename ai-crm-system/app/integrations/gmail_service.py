"""
Gmail / outbound email integration.

Demo: logs only. Structure is ready for OAuth2 + Gmail API (`users.messages.send`).
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Future Gmail API (placeholders — do not require google libs in demo)
# ---------------------------------------------------------------------------
#
# 1) Store refresh token securely (e.g. encrypted column or vault), not in code:
#    - GMAIL_OAUTH_REFRESH_TOKEN
#    - GMAIL_OAUTH_CLIENT_ID / GMAIL_OAUTH_CLIENT_SECRET
#
# 2) Exchange refresh token for access token, build service:
#    from google.oauth2.credentials import Credentials
#    from googleapiclient.discovery import build
#    creds = Credentials(
#        None,
#        refresh_token=settings.gmail_oauth_refresh_token,
#        token_uri="https://oauth2.googleapis.com/token",
#        client_id=settings.gmail_oauth_client_id,
#        client_secret=settings.gmail_oauth_client_secret,
#    )
#    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
#
# 3) RFC 2822 raw message base64url, then:
#    service.users().messages().send(userId="me", body={"raw": raw}).execute()


def send_email(to: str, subject: str, body: str) -> dict[str, Any]:
    """
    Send an outbound email.

    Current behaviour: mock — structured log only (safe for demos).

    When `GMAIL_SEND_ENABLED` is true and credentials are wired, replace the
    body below with Gmail API `users.messages.send` (see module docstring).
    """
    to_addr = (to or "").strip()
    subj = (subject or "").strip()
    text = body or ""
    gmail_enabled = bool(settings.gmail_send_enabled)

    if not to_addr:
        logger.warning("gmail_service.send_email skipped: empty recipient")
        return {"ok": False, "detail": "empty_to", "provider": "mock"}

    # Mock path (default)
    if not gmail_enabled:
        logger.info(
            "[gmail:mock] to=%s subject=%s bytes=%s (set GMAIL_SEND_ENABLED=true after OAuth setup)",
            to_addr,
            subj[:120],
            len(text.encode("utf-8", errors="ignore")),
        )
        return {
            "ok": True,
            "detail": "mock_logged",
            "provider": "mock",
            "to": to_addr,
            "subject": subj,
        }

    # Reserved for real send — still mock until google client is added
    logger.warning(
        "GMAIL_SEND_ENABLED is true but Gmail API client is not bundled; logging only. to=%s",
        to_addr,
    )
    return {
        "ok": False,
        "detail": "gmail_client_not_configured",
        "provider": "gmail_pending",
        "to": to_addr,
    }
