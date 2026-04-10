"""Retries for Groq (OpenAI SDK) rate limits (429)."""

from __future__ import annotations

import logging
import re
import time

from openai import RateLimitError

from app.services.groq_llm import groq_chat_completion

logger = logging.getLogger(__name__)


def _retry_delay_seconds(exc: BaseException, attempt: int) -> float:
    msg = str(exc)
    m = re.search(r"retry in ([0-9.]+)\s*s", msg, re.I)
    if m:
        return min(float(m.group(1)) + 1.0, 120.0)
    return min(4.0 * (2**attempt), 90.0)


def groq_chat_with_retry(
    prompt: str,
    *,
    json_mode: bool,
    max_attempts: int = 3,
) -> str:
    """
    Call Groq chat with retries on 429. Re-raises RateLimitError after last attempt.
    """
    last: BaseException | None = None
    for attempt in range(max_attempts):
        try:
            return groq_chat_completion(prompt, json_mode=json_mode)
        except RateLimitError as e:
            last = e
            if attempt == max_attempts - 1:
                raise
            delay = _retry_delay_seconds(e, attempt)
            logger.warning(
                "Groq rate limited (429); sleeping %.1fs then retry %s/%s",
                delay,
                attempt + 2,
                max_attempts,
            )
            time.sleep(delay)
    assert last is not None
    raise last
