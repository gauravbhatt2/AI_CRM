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

class GenerateEmailRequest(BaseModel):
    record_id: int | None = None
    # Context passed directly from frontend
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
    """Check if the global system user has active Google credentials by doing a LIVE check with Google."""
    import urllib.request
    import urllib.error
    import json as _json
    
    try:
        creds = google_service.get_credentials_for_user(db)
        if not creds:
            return {"connected": False, "reason": "No credentials saved"}
        
        # Refresh expired tokens first
        if creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            try:
                creds.refresh(Request())
                # Save refreshed token
                google_service.save_credentials(db, creds)
            except Exception as refresh_err:
                # Refresh failed — token likely revoked (user removed from OAuth test users)
                return {"connected": False, "reason": f"Token refresh failed: {str(refresh_err)}"}
        
        if not creds.token:
            return {"connected": False, "reason": "No access token"}
        
        # Make a live call to Google's tokeninfo endpoint to verify the token is truly accepted
        try:
            req = urllib.request.Request(
                f"https://oauth2.googleapis.com/tokeninfo?access_token={creds.token}"
            )
            resp = urllib.request.urlopen(req, timeout=5)
            token_info = _json.loads(resp.read().decode("utf-8"))
            # Token is valid if it has an email or expiry
            if token_info.get("expires_in") or token_info.get("email"):
                return {"connected": True, "email": token_info.get("email", ""), "expires_in": token_info.get("expires_in")}
            return {"connected": False, "reason": "Token invalid per Google"}
        except urllib.error.HTTPError as e:
            # 400 = invalid_token — token revoked or user removed
            err_body = e.read().decode("utf-8") if hasattr(e, "read") else ""
            return {"connected": False, "reason": f"Google rejected token: {err_body}"}
        except Exception as live_err:
            # Network issue etc — fall back to local validation
            if creds.valid:
                return {"connected": True}
            return {"connected": False, "reason": str(live_err)}
    except Exception as e:
        return {"connected": False, "reason": str(e)}


@router.post("/gmail/generate")
def generate_email_endpoint(payload: GenerateEmailRequest, db: Session = Depends(get_db)):
    """Generate email subject and body using Groq based on CRM record context."""
    from app.services.groq_llm import groq_chat_completion
    import json
    
    # Use context passed directly from frontend (preferred)
    summary = payload.summary
    pain_points = payload.pain_points
    next_action = payload.next_action
    mentioned_company = payload.mentioned_company
    to_email = ""
    
    # Optional: enrich from DB if record_id provided and context missing
    if payload.record_id and not summary:
        record = db.query(CrmRecord).filter(CrmRecord.id == payload.record_id).first()
        if record:
            summary = record.summary
            pain_points = record.pain_points
            next_action = record.next_action
            mentioned_company = record.mentioned_company
    
    # Try to get email from linked contact
    contact_id = payload.contact_id
    if contact_id:
        contact = db.query(Contact).filter(Contact.id == contact_id).first()
        if contact and contact.email:
            to_email = contact.email

    if not summary and not pain_points and not next_action:
        raise HTTPException(status_code=400, detail="No CRM context available to generate email. Ensure the record has a summary or pain points.")
        
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
    
    try:
        completion_text = groq_chat_completion(prompt, json_mode=True, temperature=0.3)
        
        # Sanitize potential markdown wrap
        cleaned_text = completion_text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        if cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]
            
        data = json.loads(cleaned_text.strip())
        return {
            "to": to_email,
            "subject": data.get("subject", ""),
            "body": data.get("body", "")
        }
    except Exception as e:
        print(f"Error generating email: {str(e)} | Output was: {completion_text if 'completion_text' in locals() else 'None'}")
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {str(e)}")

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
