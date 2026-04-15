from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.db.models import CrmRecord
from app.services.hubspot_service import (
    create_deal_from_record,
    fetch_account_link_hints,
    hubspot_deal_record_url,
)

router = APIRouter(prefix="/hubspot", tags=["hubspot"])


class HubspotPushResponse(BaseModel):
    message: str = Field(..., description="Sync status")
    record_id: int
    hubspot_deal_id: str = Field(..., description="HubSpot CRM deal id (search or open in UI)")
    hubspot_portal_id: str | None = Field(
        default=None,
        description="HubSpot portal (Hub) id — must match the account you open in the browser",
    )
    deal_record_url: str | None = Field(
        default=None,
        description="Direct link to the deal record (if portal id was resolved)",
    )
    hubspot_contact_id: str | None = Field(
        default=None,
        description="HubSpot contact id if created or linked",
    )
    hubspot_company_id: str | None = Field(
        default=None,
        description="HubSpot company id if created or linked",
    )
    hubspot_note_id: str | None = Field(
        default=None,
        description="HubSpot note / engagement id if transcript was attached",
    )
    hubspot: dict


@router.post("/push/{record_id}", response_model=HubspotPushResponse)
def push_record_to_hubspot(record_id: int, db: Session = Depends(get_db)) -> HubspotPushResponse:
    record = db.get(CrmRecord, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="CRM record not found")

    try:
        sync = create_deal_from_record(record)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"HubSpot sync failed: {exc}") from exc

    deal_body = sync.get("deal") if isinstance(sync, dict) else sync
    if not isinstance(deal_body, dict):
        raise HTTPException(status_code=500, detail="Invalid HubSpot sync response")

    deal_id = str(deal_body.get("id", "")).strip()
    token = (settings.hubspot_api_key or "").strip()
    portal_id, ui_domain = fetch_account_link_hints(token) if token else (None, None)
    deal_url = (
        hubspot_deal_record_url(portal_id, deal_id, ui_domain) if portal_id else None
    )

    return HubspotPushResponse(
        message="Synced to HubSpot",
        record_id=record_id,
        hubspot_deal_id=deal_id,
        hubspot_portal_id=portal_id,
        deal_record_url=deal_url,
        hubspot_contact_id=sync.get("hubspot_contact_id") if isinstance(sync, dict) else None,
        hubspot_company_id=sync.get("hubspot_company_id") if isinstance(sync, dict) else None,
        hubspot_note_id=sync.get("hubspot_note_id") if isinstance(sync, dict) else None,
        hubspot=deal_body,
    )
