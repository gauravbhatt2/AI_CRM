"""HTTP endpoints for agentic CRM helpers (next action, follow-up, deal chat)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.chat_agent import chat_with_deal
from app.agents.followup_agent import generate_followup_email, generate_whatsapp_message
from app.agents.next_action_agent import suggest_next_action
from app.agents.tools import get_crm_record
from app.api.deps import get_db

router = APIRouter(prefix="/agents", tags=["agents"])


class NextActionResponse(BaseModel):
    record_id: int
    next_action: str = Field(..., description="Rule- or LLM-backed next best action (max ~10 words)")


class FollowupResponse(BaseModel):
    record_id: int
    email: str
    whatsapp: str


class ChatTurn(BaseModel):
    """Single prior message for lightweight context (optional)."""

    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Question about the deal / record")
    record_id: int = Field(..., ge=1, description="crm_records.id")
    conversation: list[ChatTurn] | None = Field(
        default=None,
        max_length=6,
        description="Optional last turns (e.g. up to 3 exchanges) for short memory",
    )


class ChatResponse(BaseModel):
    response: str = Field(..., description="Assistant reply grounded in CRM record fields")


@router.post("/next-action/{record_id}", response_model=NextActionResponse)
def post_next_action(record_id: int, db: Session = Depends(get_db)) -> NextActionResponse:
    rec = get_crm_record(db, record_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="CRM record not found")
    return NextActionResponse(record_id=record_id, next_action=suggest_next_action(rec))


@router.post("/followup/{record_id}", response_model=FollowupResponse)
def post_followup(record_id: int, db: Session = Depends(get_db)) -> FollowupResponse:
    rec = get_crm_record(db, record_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="CRM record not found")
    return FollowupResponse(
        record_id=record_id,
        email=generate_followup_email(rec),
        whatsapp=generate_whatsapp_message(rec),
    )


@router.post("/chat", response_model=ChatResponse)
def post_deal_chat(body: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    rec = get_crm_record(db, body.record_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="CRM record not found")
    hist = [{"role": t.role, "content": t.content} for t in (body.conversation or [])]
    return ChatResponse(response=chat_with_deal(body.query, rec, conversation_history=hist or None))
