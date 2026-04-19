"""
Groq OpenAI-compatible API client (https://api.groq.com/openai/v1).

Set GROQ_API_KEY and GROQ_MODEL in the environment or .env file.
"""

from __future__ import annotations

from typing import Any

from openai import OpenAI

from app.core.config import settings

GROQ_BASE_URL = "https://api.groq.com/openai/v1"

_client: OpenAI | None = None


def get_groq_client() -> OpenAI:
    global _client
    if _client is None:
        key = (settings.groq_api_key or "").strip()
        if not key:
            raise RuntimeError("GROQ_API_KEY is not set")
        _client = OpenAI(api_key=key, base_url=GROQ_BASE_URL)
    return _client


def groq_chat_completion(
    prompt: str,
    *,
    json_mode: bool = True,
    temperature: float = 0.0,
    top_p: float = 1.0,
    max_tokens: int = 4096,
    model: str | None = None,
) -> str:
    """Single chat completion; returns assistant message text.

    Defaults favor reproducibility (temperature 0, top_p 1) for extraction tasks.
    """
    m = (model or settings.groq_model or "").strip()
    if not m:
        raise RuntimeError("GROQ_MODEL is not set")
    client = get_groq_client()
    kwargs: dict[str, Any] = {
        "model": m,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = client.chat.completions.create(**kwargs)
    content = resp.choices[0].message.content
    return (content or "").strip()
