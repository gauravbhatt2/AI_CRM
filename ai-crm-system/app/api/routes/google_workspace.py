import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.api.deps import get_db
from app.services import google_service
from app.db.models import CrmRecord, Contact, Deal

router = APIRouter(tags=["Google Workspace Integration"])

class EmailMessageSchema(BaseModel):
    to: EmailStr
    subject: str
    body: str
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

# In-memory store for OAuth flows (for PKCE code_verifier state)
oauth_states = {}

@router.get("/auth/")
def auth_google():
    """Start Google OAuth flow"""
    flow = google_service.get_oauth_flow()
    auth_url, state = flow.authorization_url(access_type='offline', prompt='consent')
    oauth_states[state] = flow
    return {"url": auth_url}

@router.get("/auth/callback")
def auth_google_callback(state: str, code: str, db: Session = Depends(get_db)):
    """Callback for Google OAuth"""
    try:
        flow = oauth_states.get(state)
        if not flow:
            raise ValueError("OAuth state not found. Please initiate the login from the CRM again.")
        
        flow.fetch_token(code=code)
        creds = flow.credentials
        google_service.save_credentials(db, creds)
        del oauth_states[state]
        
        # Redirect back to the frontend
        return RedirectResponse(url="http://localhost:5174/")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth Flow Failed: {e}")

@router.get("/status/")
def check_google_status(db: Session = Depends(get_db)):
    """Check if the global system user has active Google credentials."""
    try:
        creds = google_service.get_credentials_for_user(db)
        if creds and creds.valid:
            return {"connected": True}
        # If credentials exist but are expired, refresh them
        if creds and creds.expired and creds.refresh_token:
            return {"connected": True}
    except Exception:
        pass
    
    return {"connected": False}

@router.post("/gmail/send")
def send_email(payload: EmailMessageSchema, db: Session = Depends(get_db)):
    """Send an email and log CRMRecord"""
    creds = google_service.get_credentials_for_user(db)
    if not creds:
        raise HTTPException(status_code=401, detail="Google authentication required. Please connect account.")
    
    try:
        # Send Email
        result = google_service.send_gmail_message(
            creds, to=payload.to, subject=payload.subject, message_text=payload.body
        )

        # Log to CRM
        crm_record = CrmRecord(
            content=f"Sent email to {payload.to}\\nSubject: {payload.subject}\\nBody: {payload.body}",
            source_type="email_sent",
            deal_id=payload.deal_id,
            contact_id=payload.contact_id,
            interaction_type="outbound_email"
        )
        db.add(crm_record)
        db.commit()

        return {"status": "success", "message_id": result.get("id")}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/calendar/schedule")
def schedule_event(payload: CalendarEventSchema, db: Session = Depends(get_db)):
    """Schedule event and log CRMRecord"""
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
            attendees=payload.attendees
        )

        # Log to CRM
        crm_record = CrmRecord(
            content=f"Scheduled Calendar Event: {payload.title}\\nAt: {payload.start_time}\\nAttendees: {payload.attendees}",
            source_type="calendar_event",
            deal_id=payload.deal_id,
            contact_id=payload.contact_id,
            interaction_type="outbound_meeting"
        )
        db.add(crm_record)
        db.commit()

        return {"status": "success", "event_link": result.get("htmlLink")}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
