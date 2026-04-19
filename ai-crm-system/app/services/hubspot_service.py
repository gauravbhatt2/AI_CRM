"""HubSpot CRM sync service — deals, mapped properties, contacts, companies, notes."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import requests

from app.core.config import settings
from app.services.hubspot_client import (
    associate_deal_company,
    associate_deal_contact,
    create_company,
    create_contact,
    create_note_on_deal,
    search_company_by_name,
    search_contact_by_email,
    search_contact_by_phone,
)
from app.utils.budget import parse_budget_to_int
from app.utils.hubspot_product import clean_product_for_hubspot

logger = logging.getLogger(__name__)

_HUBSPOT_DEALS_URL = "https://api.hubapi.com/crm/v3/objects/deals"
_ACCOUNT_INFO_URL = "https://api.hubapi.com/account-info/v3/details"
_PIPELINES_DEALS_URL = "https://api.hubapi.com/crm/v3/pipelines/deals"


def fetch_first_stage_id_for_pipeline(token: str, pipeline_id: str) -> str | None:
    """
    Return internal id of the first stage (by displayOrder) for a deal pipeline.

    HubSpot portals often use numeric stage ids (e.g. 3485319879), not legacy names
    like appointmentscheduled — resolve at runtime when HUBSPOT_DEAL_STAGE_ID is unset.
    """
    token = (token or "").strip()
    if not token:
        return None
    try:
        res = requests.get(
            _PIPELINES_DEALS_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        if res.status_code != 200:
            return None
        data = res.json()
        results = data.get("results") or []
        target = None
        for pl in results:
            if str(pl.get("id")) == str(pipeline_id):
                target = pl
                break
        if target is None and results:
            target = results[0]
        if not target:
            return None
        stages = list(target.get("stages") or [])

        def _order(s: dict) -> int:
            try:
                return int(s.get("displayOrder", 0) or 0)
            except (TypeError, ValueError):
                return 0

        stages.sort(key=_order)
        if not stages:
            return None
        sid = stages[0].get("id")
        return str(sid) if sid is not None else None
    except (TypeError, ValueError, requests.RequestException, KeyError):
        return None


def resolve_deal_stage_id(token: str, pipeline_id: str, configured_stage: str) -> str:
    """Use configured stage if set; otherwise first stage of the pipeline from HubSpot."""
    c = (configured_stage or "").strip()
    if c:
        return c
    auto = fetch_first_stage_id_for_pipeline(token, pipeline_id)
    if auto:
        return auto
    raise RuntimeError(
        "Could not resolve a deal stage for this HubSpot portal. "
        "Set HUBSPOT_DEAL_STAGE_ID in .env to one of your valid stage ids "
        f'(error messages list them under pipelineId={pipeline_id!r}), '
        "or ensure the private app can read pipelines (try GET /crm/v3/pipelines/deals)."
    )


def fetch_account_link_hints(token: str) -> tuple[str | None, str | None]:
    """
    Portal id and UI hostname for deep links (PAT is opaque).

    HubSpot uses regional app hosts (e.g. app-na2.hubspot.com). The account-info API
    returns `uiDomain` — use it instead of hardcoding app.hubspot.com or links 404/wrong portal.
    """
    token = (token or "").strip()
    if not token:
        return None, None
    try:
        res = requests.get(
            _ACCOUNT_INFO_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        if res.status_code != 200:
            return None, None
        data = res.json()
        pid = data.get("portalId")
        portal_id = str(int(pid)) if pid is not None else None
        raw_host = (data.get("uiDomain") or "").strip()
        if raw_host:
            raw_host = raw_host.rstrip("/").removeprefix("https://").removeprefix("http://").split("/")[0]
        ui_domain = raw_host or None
        return portal_id, ui_domain
    except (TypeError, ValueError, requests.RequestException):
        return None, None


def hubspot_deal_record_url(
    portal_id: str, deal_id: str, ui_domain: str | None = None
) -> str:
    """Deals object type id 0-3 is the standard deal object in HubSpot."""
    host = (ui_domain or "app.hubspot.com").strip().lower()
    host = host.removeprefix("https://").removeprefix("http://").split("/")[0]
    return f"https://{host}/contacts/{portal_id}/record/0-3/{deal_id}"


def _split_name(name: str) -> tuple[str, str]:
    name = (name or "").strip()
    if not name:
        return "", ""
    parts = name.split()
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def _contact_hints_from_record(record: Any) -> dict[str, str]:
    """Email / phone / name hints for HubSpot contact search & create."""
    cf = getattr(record, "custom_fields", None) or {}
    if not isinstance(cf, dict):
        cf = {}
    content = getattr(record, "content", "") or ""
    email = (cf.get("email") or cf.get("contact_email") or "").strip()
    phone = (cf.get("phone") or cf.get("phone_number") or cf.get("mobile") or "").strip()
    raw_name = (cf.get("contact_name") or cf.get("customer_name") or "").strip()
    if not email:
        em = re.search(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", content)
        if em:
            email = em.group(0)
    if not phone:
        pm = re.search(
            r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
            content,
        )
        if pm:
            phone = pm.group(0).strip()
    if not raw_name:
        parts = getattr(record, "participants", None) or []
        if isinstance(parts, list) and parts:
            raw_name = str(parts[0]).strip()
    first, last = _split_name(raw_name)
    return {
        "email": email,
        "phone": phone,
        "firstname": first,
        "lastname": last,
    }


def _has_contact_identity(h: dict[str, str]) -> bool:
    return bool(
        (h.get("email") or "").strip()
        or (h.get("phone") or "").strip()
        or (h.get("firstname") or "").strip()
        or (h.get("lastname") or "").strip()
    )


_VALID_INTENT = {"high", "medium", "low"}
_VALID_RISK_LEVEL = {"low", "medium", "high"}
_VALID_INTERACTION_TYPE = {"sales", "support", "inquiry", "complaint"}


def _hubspot_omit_value(value: str) -> bool:
    """Skip empty or LLM sentinel placeholders (aligned with unified extraction)."""
    s = (value or "").strip()
    if not s:
        return True
    return s.lower() in ("n/a", "na", "none", "null", "unknown")


def _deal_properties_from_record(record: Any, token: str) -> dict[str, str]:
    """Build HubSpot deal properties using ONLY the supported custom properties.

    Allowed fields (besides HubSpot defaults dealname/amount/pipeline/dealstage):
      intent, timeline, product, deal_score, risk_level, next_action,
      summary, pain_points, interaction_type, mentioned_company

    Dropdown fields are validated to exact enum values.
    Null / empty fields are omitted entirely to prevent API errors.
    """
    amount_int = parse_budget_to_int(getattr(record, "budget", ""))
    pipeline_id = (settings.hubspot_pipeline_id or "default").strip() or "default"
    stage_id = resolve_deal_stage_id(
        token,
        pipeline_id,
        (settings.hubspot_deal_stage_id or "").strip(),
    )

    props: dict[str, str] = {
        "dealname": f"AI Deal {record.id}",
        "pipeline": pipeline_id,
        "dealstage": stage_id,
    }

    if amount_int:
        props["amount"] = str(amount_int)

    intent = str(getattr(record, "intent", "") or "").strip().lower()
    if intent in _VALID_INTENT:
        props["intent"] = intent

    timeline = str(getattr(record, "timeline", "") or "").strip()
    if timeline and not _hubspot_omit_value(timeline):
        props["timeline"] = timeline[:65000]

    raw_product = str(getattr(record, "product", "") or "").strip()
    if raw_product and not _hubspot_omit_value(raw_product):
        clean_prod, _ = clean_product_for_hubspot(raw_product)
        if clean_prod:
            props["product"] = clean_prod

    deal_score = getattr(record, "deal_score", None)
    if deal_score is not None and int(deal_score or 0) > 0:
        props["deal_score"] = str(int(deal_score))

    risk_level = str(getattr(record, "risk_level", "") or "").strip().lower()
    if risk_level in _VALID_RISK_LEVEL:
        props["risk_level"] = risk_level

    next_action = str(getattr(record, "next_action", "") or "").strip()
    if next_action and not _hubspot_omit_value(next_action):
        props["next_action"] = next_action[:65000]

    summary = str(getattr(record, "summary", "") or "").strip()
    if summary and not _hubspot_omit_value(summary):
        props["summary"] = summary[:65000]

    pain_points = str(getattr(record, "pain_points", "") or "").strip()
    if pain_points and not _hubspot_omit_value(pain_points):
        props["pain_points"] = pain_points[:65000]

    interaction_type = str(getattr(record, "interaction_type", "") or "").strip().lower()
    if interaction_type in _VALID_INTERACTION_TYPE:
        props["interaction_type"] = interaction_type

    mentioned_company = str(getattr(record, "mentioned_company", "") or "").strip()
    if mentioned_company and not _hubspot_omit_value(mentioned_company):
        props["mentioned_company"] = mentioned_company[:65000]

    return props


_HUBSPOT_REQUIRED_KEYS = {"dealname", "pipeline", "dealstage"}


def _extract_rejected_properties(error_text: str) -> list[str]:
    """Parse HubSpot 400 errors to find property names that don't exist in the portal."""
    rejected: list[str] = []
    for m in re.finditer(r"Property values were not valid.*?\"name\":\"(\w+)\"", error_text):
        name = m.group(1)
        if name not in _HUBSPOT_REQUIRED_KEYS:
            rejected.append(name)
    for m in re.finditer(r"\"(\w+)\" (?:does not exist|is not valid|was not found)", error_text):
        name = m.group(1)
        if name not in _HUBSPOT_REQUIRED_KEYS:
            rejected.append(name)
    return list(dict.fromkeys(rejected))


def _post_deal(token: str, properties: dict[str, str]) -> requests.Response:
    return requests.post(
        _HUBSPOT_DEALS_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"properties": properties},
        timeout=30,
    )


def create_deal_from_record(record: Any) -> dict[str, Any]:
    """
    Create HubSpot deal + map fields, optional company/contact + note.

    Returns dict with keys: deal (HubSpot deal JSON), hubspot_contact_id, hubspot_company_id,
    hubspot_note_id (each optional except deal).
    """
    token = (settings.hubspot_api_key or "").strip()
    if not token:
        raise RuntimeError("HUBSPOT_API_KEY is not configured.")

    properties = _deal_properties_from_record(record, token)
    res = _post_deal(token, properties)

    if res.status_code == 400:
        rejected = _extract_rejected_properties(res.text or "")
        if rejected:
            for prop in rejected:
                properties.pop(prop, None)
            logger.warning(
                "Retrying HubSpot deal creation after dropping unsupported properties: %s",
                rejected,
            )
            res = _post_deal(token, properties)

    if res.status_code not in (200, 201):
        detail = res.text
        try:
            detail = json.dumps(res.json())
        except (ValueError, TypeError):
            pass
        raise RuntimeError(f"HubSpot deal creation failed ({res.status_code}): {detail}")

    deal_body = res.json()
    deal_id = str(deal_body.get("id") or "").strip()
    if not deal_id:
        raise RuntimeError(
            f"HubSpot returned {res.status_code} but no deal id in body: {deal_body!r}"
        )

    hubspot_contact_id: str | None = None
    hubspot_company_id: str | None = None
    hubspot_note_id: str | None = None

    cf = getattr(record, "custom_fields", None) or {}
    if not isinstance(cf, dict):
        cf = {}

    mc = str(getattr(record, "mentioned_company", "") or cf.get("mentioned_company") or "").strip()
    if mc:
        try:
            company_hs_id = search_company_by_name(token, mc) or create_company(token, mc)
            if company_hs_id:
                hubspot_company_id = company_hs_id
                associate_deal_company(token, deal_id, company_hs_id)
        except Exception:
            logger.exception("HubSpot company sync failed for record %s", getattr(record, "id", "?"))

    # Contact
    hints = _contact_hints_from_record(record)
    if _has_contact_identity(hints):
        try:
            contact_hs_id: str | None = None
            if hints.get("email"):
                contact_hs_id = search_contact_by_email(token, hints["email"])
            if not contact_hs_id and hints.get("phone"):
                contact_hs_id = search_contact_by_phone(token, hints["phone"])
            if not contact_hs_id:
                contact_hs_id = create_contact(
                    token,
                    email=hints.get("email") or "",
                    phone=hints.get("phone") or "",
                    firstname=hints.get("firstname") or "",
                    lastname=hints.get("lastname") or "",
                )
            if contact_hs_id:
                hubspot_contact_id = contact_hs_id
                associate_deal_contact(token, deal_id, contact_hs_id)
        except Exception:
            logger.exception("HubSpot contact sync failed for record %s", getattr(record, "id", "?"))

    # Transcript as note
    content = (getattr(record, "content", "") or "").strip()
    if content:
        try:
            nid = create_note_on_deal(token, deal_id, content)
            if nid:
                hubspot_note_id = str(nid)
        except Exception:
            logger.exception("HubSpot note creation failed for record %s", getattr(record, "id", "?"))

    return {
        "deal": deal_body,
        "hubspot_contact_id": hubspot_contact_id,
        "hubspot_company_id": hubspot_company_id,
        "hubspot_note_id": hubspot_note_id,
    }
