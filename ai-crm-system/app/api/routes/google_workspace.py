"""HTTP routes for Google Workspace (Gmail + Calendar), from mailNDcalendar branch."""

import datetime
import json as _json
import urllib.error
import urllib.request

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.db.models import Contact, CrmRecord
from app.services.groq_llm import groq_chat_completion
import app.services.google_service as google_service

router = APIRouter(tags=["Google Workspace Integration"])

oauth_states: dict = {}


class EmailMessageSchema(BaseModel):
    to: EmailStr
    subject: str
    body: str
    contact_id: int | None = None
    deal_id: int | None = None


class GenerateEmailRequest(BaseModel):
    record_id: int | None = None
    summary: str | None = None
    pain_points: str | None = None
    next_action: str | None = None
    mentioned_company: str | None = None
    contact_id: int | None = None
    deal_id: int | None = None


class CalendarEventSchema(BaseModel):
    title: str
    description: str
    start_time: datetime.datetime
    end_time: datetime.datetime
    attendees: list[EmailStr] = []
    contact_id: int | None = None
    deal_id: int | None = None


@router.get("/auth")
def auth_google(request: Request):
    """Start Google OAuth flow."""
    flow = google_service.get_oauth_flow(str(request.base_url))
    auth_url, state = flow.authorization_url(access_type="offline", prompt="consent")
    oauth_states[state] = flow
    return {
        "url": auth_url,
        "redirect_uri": google_service.get_google_redirect_uri(str(request.base_url)),
    }


@router.get("/auth/callback")
def auth_google_callback(state: str, code: str, db: Session = Depends(get_db)):
    """Callback for Google OAuth."""
    try:
        flow = oauth_states.get(state)
        if not flow:
            raise ValueError("OAuth state not found. Please initiate the login from the CRM again.")

        flow.fetch_token(code=code)
        creds = flow.credentials
        google_service.save_credentials(db, creds)
        del oauth_states[state]

        redirect = (settings.google_oauth_success_redirect or "http://localhost:5173/").strip()
        return RedirectResponse(url=redirect)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth Flow Failed: {e}") from e


@router.post("/auth/signout")
def signout_google(db: Session = Depends(get_db)):
    """Clear stored Google OAuth credentials (disconnect in this app)."""
    google_service.clear_credentials(db)
    return {"status": "signed_out"}


@router.get("/status")
def check_google_status(db: Session = Depends(get_db)):
    """Check if saved Google credentials work with a live tokeninfo call."""
    try:
        creds = google_service.get_credentials_for_user(db)
        if not creds:
            return {"connected": False, "reason": "No credentials saved"}

        if creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request

            try:
                creds.refresh(Request())
                google_service.save_credentials(db, creds)
            except Exception as refresh_err:
                return {"connected": False, "reason": f"Token refresh failed: {str(refresh_err)}"}

        if not creds.token:
            return {"connected": False, "reason": "No access token"}

        try:
            req = urllib.request.Request(
                f"https://oauth2.googleapis.com/tokeninfo?access_token={creds.token}"
            )
            resp = urllib.request.urlopen(req, timeout=5)
            token_info = _json.loads(resp.read().decode("utf-8"))
            if token_info.get("expires_in") or token_info.get("email"):
                return {
                    "connected": True,
                    "email": token_info.get("email", ""),
                    "expires_in": token_info.get("expires_in"),
                }
            return {"connected": False, "reason": "Token invalid per Google"}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8") if hasattr(e, "read") else ""
            return {"connected": False, "reason": f"Google rejected token: {err_body}"}
        except Exception as live_err:
            if creds.valid:
                return {"connected": True}
            return {"connected": False, "reason": str(live_err)}
    except Exception as e:
        return {"connected": False, "reason": str(e)}


@router.post("/gmail/generate")
def generate_email_endpoint(payload: GenerateEmailRequest, db: Session = Depends(get_db)):
    """Generate email subject and body using Groq from CRM context."""
    summary = payload.summary
    pain_points = payload.pain_points
    next_action = payload.next_action
    mentioned_company = payload.mentioned_company
    to_email = ""

    if payload.record_id and not summary:
        record = db.query(CrmRecord).filter(CrmRecord.id == payload.record_id).first()
        if record:
            summary = record.summary
            pain_points = record.pain_points
            next_action = record.next_action
            mentioned_company = record.mentioned_company

    contact_id = payload.contact_id
    if contact_id:
        contact = db.query(Contact).filter(Contact.id == contact_id).first()
        if contact and contact.email:
            to_email = contact.email

    if not summary and not pain_points and not next_action:
        raise HTTPException(
            status_code=400,
            detail="No CRM context available to generate email. Ensure the record has a summary or pain points.",
        )

    prompt = f"""
    Write a short, professional, and highly contextual outbound email to a prospect.
    The goal is to follow up on the next steps based on this CRM interaction record.

    Summary of Interaction: {summary or 'N/A'}
    Pain Points: {pain_points or 'N/A'}
    Next Action: {next_action or 'N/A'}
    Company: {mentioned_company or 'N/A'}

    Respond STRICTLY in JSON format with exactly two keys:
    "subject": "The email subject line"
    "body": "The email body in plain text, concise and professional, 3-5 sentences."
    """

    completion_text = ""
    try:
        completion_text = groq_chat_completion(prompt, json_mode=True, temperature=0.3)

        cleaned_text = completion_text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        if cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]

        data = _json.loads(cleaned_text.strip())
        return {
            "to": to_email,
            "subject": data.get("subject", ""),
            "body": data.get("body", ""),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"LLM generation failed: {str(e)}",
        ) from e


@router.post("/gmail/send")
def send_email(payload: EmailMessageSchema, db: Session = Depends(get_db)):
    """Send an email and log a CRM record."""
    creds = google_service.get_credentials_for_user(db)
    if not creds:
        raise HTTPException(status_code=401, detail="Google authentication required. Please connect account.")

    try:
        result = google_service.send_gmail_message(
            creds, to=payload.to, subject=payload.subject, message_text=payload.body
        )

        crm_record = CrmRecord(
            content=f"Sent email to {payload.to}\nSubject: {payload.subject}\nBody: {payload.body}",
            source_type="email_sent",
            deal_id=payload.deal_id,
            contact_id=payload.contact_id,
            interaction_type="outbound_email",
        )
        db.add(crm_record)
        db.commit()

        return {"status": "success", "message_id": result.get("id")}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/calendar/schedule")
def schedule_event(payload: CalendarEventSchema, db: Session = Depends(get_db)):
    """Schedule a calendar event and log a CRM record."""
    creds = google_service.get_credentials_for_user(db)
    if not creds:
        raise HTTPException(status_code=401, detail="Google authentication required. Please connect account.")

    try:
        result = google_service.create_calendar_event(
            creds,
            title=payload.title,
            description=payload.description,
            start_time=payload.start_time,
            end_time=payload.end_time,
            attendees=[str(a) for a in payload.attendees],
        )

        crm_record = CrmRecord(
            content=(
                f"Scheduled Calendar Event: {payload.title}\nAt: {payload.start_time}\n"
                f"Attendees: {payload.attendees}"
            ),
            source_type="calendar_event",
            deal_id=payload.deal_id,
            contact_id=payload.contact_id,
            interaction_type="outbound_meeting",
        )
        db.add(crm_record)
        db.commit()

        return {"status": "success", "event_link": result.get("htmlLink")}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
