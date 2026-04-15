"""
Low-level HubSpot REST helpers (contacts, companies, deals, associations, notes).

Requires private app scopes: deals, contacts, companies read/write; engagements or notes.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

BASE = "https://api.hubapi.com"


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token.strip()}",
        "Content-Type": "application/json",
    }


def hs_request(
    method: str,
    path: str,
    token: str,
    *,
    json_body: dict[str, Any] | None = None,
    timeout: int = 30,
) -> requests.Response:
    url = path if path.startswith("http") else f"{BASE}{path}"
    return requests.request(
        method,
        url,
        headers=_headers(token),
        json=json_body,
        timeout=timeout,
    )


def search_contact_by_email(token: str, email: str) -> str | None:
    email = (email or "").strip().lower()
    if not email:
        return None
    body = {
        "filterGroups": [
            {
                "filters": [
                    {
                        "propertyName": "email",
                        "operator": "EQ",
                        "value": email,
                    }
                ]
            }
        ],
        "properties": ["email", "firstname", "lastname", "phone", "mobilephone"],
        "limit": 1,
    }
    r = hs_request("POST", "/crm/v3/objects/contacts/search", token, json_body=body)
    if r.status_code != 200:
        logger.warning("HubSpot contact search (email) %s: %s", r.status_code, r.text[:300])
        return None
    results = r.json().get("results") or []
    if not results:
        return None
    return str(results[0].get("id"))


def _normalize_phone_digits(phone: str) -> str:
    return re.sub(r"\D+", "", phone or "")


def search_contact_by_phone(token: str, phone: str) -> str | None:
    digits = _normalize_phone_digits(phone)
    if len(digits) < 7:
        return None
    # Search common phone properties
    for prop in ("phone", "mobilephone", "hs_searchable_calculated_phone_number"):
        body = {
            "filterGroups": [
                {
                    "filters": [
                        {
                            "propertyName": prop,
                            "operator": "CONTAINS_TOKEN",
                            "value": digits[-10:] if len(digits) >= 10 else digits,
                        }
                    ]
                }
            ],
            "properties": ["email", "phone", "mobilephone"],
            "limit": 3,
        }
        r = hs_request("POST", "/crm/v3/objects/contacts/search", token, json_body=body)
        if r.status_code != 200:
            continue
        results = r.json().get("results") or []
        if results:
            return str(results[0].get("id"))
    return None


def create_contact(
    token: str,
    *,
    email: str = "",
    phone: str = "",
    firstname: str = "",
    lastname: str = "",
) -> str | None:
    props: dict[str, str] = {}
    if firstname:
        props["firstname"] = firstname[:256]
    if lastname:
        props["lastname"] = lastname[:256]
    if email:
        props["email"] = email[:512]
    if phone:
        props["phone"] = phone[:256]
    if not props:
        return None
    r = hs_request(
        "POST",
        "/crm/v3/objects/contacts",
        token,
        json_body={"properties": props},
    )
    if r.status_code not in (200, 201):
        logger.warning("HubSpot create contact failed %s: %s", r.status_code, r.text[:400])
        return None
    return str(r.json().get("id") or "")


def search_company_by_name(token: str, name: str) -> str | None:
    name = (name or "").strip()
    if len(name) < 2:
        return None
    body = {
        "filterGroups": [
            {
                "filters": [
                    {
                        "propertyName": "name",
                        "operator": "EQ",
                        "value": name,
                    }
                ]
            }
        ],
        "properties": ["name", "domain"],
        "limit": 1,
    }
    r = hs_request("POST", "/crm/v3/objects/companies/search", token, json_body=body)
    if r.status_code != 200:
        logger.warning("HubSpot company search %s: %s", r.status_code, r.text[:300])
        return None
    results = r.json().get("results") or []
    if not results:
        return None
    return str(results[0].get("id"))


def create_company(token: str, name: str) -> str | None:
    name = (name or "").strip()
    if len(name) < 2:
        return None
    r = hs_request(
        "POST",
        "/crm/v3/objects/companies",
        token,
        json_body={"properties": {"name": name[:512]}},
    )
    if r.status_code not in (200, 201):
        logger.warning("HubSpot create company failed %s: %s", r.status_code, r.text[:400])
        return None
    return str(r.json().get("id") or "")


def associate_deal_contact(token: str, deal_id: str, contact_id: str) -> bool:
    """v4 batch association deal -> contact (default deal_to_contact)."""
    body = {
        "inputs": [
            {
                "from": {"id": str(deal_id)},
                "to": {"id": str(contact_id)},
                "type": "deal_to_contact",
            }
        ]
    }
    last: requests.Response | None = None
    for path in (
        "/crm/v4/associations/deal/contact/batch/create",
        "/crm/v4/associations/deals/contacts/batch/create",
    ):
        last = hs_request("POST", path, token, json_body=body)
        if last.status_code in (200, 201, 204):
            return True
    logger.warning(
        "HubSpot deal-contact association failed: %s",
        (last.text[:500] if last else ""),
    )
    return False


def associate_deal_company(token: str, deal_id: str, company_id: str) -> bool:
    body = {
        "inputs": [
            {
                "from": {"id": str(deal_id)},
                "to": {"id": str(company_id)},
                "type": "deal_to_company",
            }
        ]
    }
    last: requests.Response | None = None
    for path in (
        "/crm/v4/associations/deal/company/batch/create",
        "/crm/v4/associations/deals/companies/batch/create",
    ):
        last = hs_request("POST", path, token, json_body=body)
        if last.status_code in (200, 201, 204):
            return True
    logger.warning(
        "HubSpot deal-company association failed: %s",
        (last.text[:500] if last else ""),
    )
    return False


def create_note_on_deal(token: str, deal_id: str, body_text: str) -> str | None:
    """
    Create a timeline note on the deal via Engagements API (broadly compatible with private apps).
    """
    text = (body_text or "").strip()
    if not text:
        return None
    text = text[:50000]
    deal_int = int(deal_id) if str(deal_id).isdigit() else deal_id
    ms = int(time.time() * 1000)
    payload = {
        "engagement": {"active": True, "type": "NOTE", "timestamp": ms},
        "metadata": {"body": text},
        "associations": {"dealIds": [deal_int]},
    }
    r = hs_request(
        "POST",
        f"{BASE}/engagements/v1/engagements",
        token,
        json_body=payload,
        timeout=45,
    )
    if r.status_code not in (200, 201):
        logger.warning(
            "HubSpot engagement note failed %s: %s — trying CRM notes object",
            r.status_code,
            r.text[:400],
        )
        return _create_note_crm_v3(token, deal_id, text)
    data = r.json()
    eng = data.get("engagement") or {}
    return str(eng.get("id") or data.get("engagementId") or "")


def _create_note_crm_v3(token: str, deal_id: str, body_text: str) -> str | None:
    """Fallback: CRM notes object with deal association (association type id may vary by portal)."""
    ts = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    # Escape HTML minimally for note body
    safe = (
        body_text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )
    html = f"<p>{safe}</p>"
    payload = {
        "properties": {"hs_note_body": html, "hs_timestamp": ts},
        "associations": [
            {
                "to": {"id": str(deal_id)},
                "types": [
                    {
                        "associationCategory": "HUBSPOT_DEFINED",
                        "associationTypeId": 214,
                    }
                ],
            }
        ],
    }
    r = hs_request("POST", "/crm/v3/objects/notes", token, json_body=payload, timeout=45)
    if r.status_code not in (200, 201):
        logger.warning("HubSpot CRM note fallback failed %s: %s", r.status_code, r.text[:400])
        return None
    return str(r.json().get("id") or "")
