"""Google Workspace Integration Service for Gmail and Calendar."""

from __future__ import annotations

import datetime
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import OAuthCredential

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar.events",
]


def _get_client_config() -> dict:
    return {
        "web": {
            "client_id": settings.google_client_id,
            "project_id": "ai-crm-integration",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": settings.google_client_secret,
            "redirect_uris": [settings.google_redirect_uri or ""],
            "javascript_origins": [],
        }
    }


def get_oauth_flow() -> Flow:
    """Returns an OAuth Flow instance pre-configured from env logic."""
    flow = Flow.from_client_config(
        _get_client_config(),
        scopes=SCOPES,
        redirect_uri=settings.google_redirect_uri,
    )
    return flow


def get_credentials_for_user(db: Session, user_identifier: str = "global_system_user") -> Optional[Credentials]:
    """Retrieve Google OAuth Credentials from the database."""
    cred_model = db.query(OAuthCredential).filter(OAuthCredential.user_identifier == user_identifier).first()
    if not cred_model or not cred_model.token:
        return None

    creds = Credentials(
        token=cred_model.token,
        refresh_token=cred_model.refresh_token,
        token_uri=cred_model.token_uri,
        client_id=cred_model.client_id,
        client_secret=cred_model.client_secret,
        scopes=SCOPES,
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        cred_model.token = creds.token
        db.commit()

    return creds


def save_credentials(db: Session, creds: Credentials, user_identifier: str = "global_system_user") -> None:
    """Save Google OAuth Credentials to the database."""
    cred_model = db.query(OAuthCredential).filter(OAuthCredential.user_identifier == user_identifier).first()
    if not cred_model:
        cred_model = OAuthCredential(user_identifier=user_identifier)
        db.add(cred_model)

    cred_model.token = creds.token
    cred_model.refresh_token = creds.refresh_token
    cred_model.token_uri = creds.token_uri
    cred_model.client_id = creds.client_id
    cred_model.client_secret = creds.client_secret
    cred_model.scopes = ",".join(SCOPES)

    db.commit()


def clear_credentials(db: Session, user_identifier: str = "global_system_user") -> bool:
    """Remove stored Google OAuth tokens (local sign-out)."""
    cred_model = db.query(OAuthCredential).filter(OAuthCredential.user_identifier == user_identifier).first()
    if not cred_model:
        return False
    db.delete(cred_model)
    db.commit()
    return True


def send_gmail_message(creds: Credentials, to: str, subject: str, message_text: str) -> dict:
    """Send an email using the Gmail API."""
    import base64
    from email.mime.text import MIMEText

    service = build("gmail", "v1", credentials=creds)

    message = MIMEText(message_text, "html")
    message["to"] = to
    message["subject"] = subject

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    body = {"raw": raw_message}

    try:
        sent_message = service.users().messages().send(userId="me", body=body).execute()
        return sent_message
    except Exception as e:
        raise ValueError(f"An error occurred sending Gmail: {e}") from e


def create_calendar_event(
    creds: Credentials,
    title: str,
    description: str,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    attendees: list[str],
) -> dict:
    """Create a Calendar Event using the Google Calendar API."""
    service = build("calendar", "v3", credentials=creds)

    event = {
        "summary": title,
        "description": description,
        "start": {
            "dateTime": start_time.isoformat(),
            "timeZone": "UTC",
        },
        "end": {
            "dateTime": end_time.isoformat(),
            "timeZone": "UTC",
        },
        "attendees": [{"email": email} for email in attendees],
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "email", "minutes": 24 * 60},
                {"method": "popup", "minutes": 10},
            ],
        },
    }

    try:
        created_event = service.events().insert(calendarId="primary", body=event).execute()
        return created_event
    except Exception as e:
        raise ValueError(f"An error occurred creating Calendar event: {e}") from e
