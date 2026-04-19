"""Agentic CRM layer: next-best-action, follow-up drafts, deal chat."""

from app.agents.chat_agent import chat_with_deal
from app.agents.followup_agent import generate_followup_email, generate_whatsapp_message
from app.agents.next_action_agent import suggest_next_action

__all__ = [
    "chat_with_deal",
    "generate_followup_email",
    "generate_whatsapp_message",
    "suggest_next_action",
]
