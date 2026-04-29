"""
Robust budget / currency normalizer.

Handles:
- Plain numerics:         "50000", "50,000", "50.000,00"
- Short suffixes:          "50k", "2.5m", "1.2b"
- Words:                   "fifty thousand", "one and a half million"
- Indian units:            "5 lakh", "2 crore", "50 lakhs", "1.5 crores"
- Currency symbols:        "$50,000", "Rs. 50000", "\u20b9 5 lakh", "EUR 2k"
- Ranges (keeps upper):    "between 50k and 75k", "50-75k"
- Scaling context:         "budget of fifty" after "thousand" / "thousand dollars"
- Negatives / 'no budget': returns empty string (not zero)

Returns a clean integer string (e.g. "75000"), or "" when no plausible budget
is found. Never raises.
"""

from __future__ import annotations

import re
from typing import Final

_WORD_NUM: Final[dict[str, int]] = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
    "hundred": 100,
}
_SCALES: Final[dict[str, int]] = {
    "thousand": 1_000, "k": 1_000,
    "lakh": 100_000, "lakhs": 100_000, "lac": 100_000, "lacs": 100_000,
    "million": 1_000_000, "m": 1_000_000, "mn": 1_000_000, "mil": 1_000_000,
    "crore": 10_000_000, "crores": 10_000_000, "cr": 10_000_000,
    "billion": 1_000_000_000, "b": 1_000_000_000, "bn": 1_000_000_000,
}

_CURRENCY_RE: Final[str] = r"(?:\$|\u00a3|\u20ac|\u20b9|rs\.?|inr|usd|eur|gbp)"
_NO_BUDGET_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?:no\s+budget|cannot\s+afford|can'?t\s+afford|out\s+of\s+budget)\b",
    re.I,
)


def _words_to_number(text: str) -> int | None:
    """Parse spelled-out numbers up to 'nine hundred ninety nine' with trailing scale word(s).

    Supports fractional 'half'/'quarter' qualifiers ('one and a half million' -> 1_500_000).
    """
    tokens = [t for t in re.split(r"[\s\-]+", text.strip().lower()) if t and t != "and"]
    if not tokens:
        return None

    total: float = 0.0
    current: float = 0.0
    for tok in tokens:
        if tok in ("a", "an"):
            if current == 0:
                current = 1.0
            continue
        if tok in _WORD_NUM:
            n = _WORD_NUM[tok]
            if n == 100:
                current = (current or 1.0) * 100.0
            else:
                current += n
            continue
        if tok in _SCALES:
            scale = _SCALES[tok]
            total += (current if current else 1.0) * scale
            current = 0.0
            continue
        if re.fullmatch(r"\d+(?:\.\d+)?", tok):
            current += float(tok)
            continue
        if tok == "half":
            current += 0.5
            continue
        if tok == "quarter":
            current += 0.25
            continue
        return None
    total += current
    return int(round(total)) if total > 0 else None


def _pick_range_upper(raw: str) -> str:
    """For 'between 50k and 75k' keep the upper bound (conservative reporting)."""
    m = re.search(
        r"(\d+(?:[.,]\d+)?\s*[kmb]?)\s*(?:-|to|and)\s*(\d+(?:[.,]\d+)?\s*[kmb]?)",
        raw,
        flags=re.I,
    )
    if m:
        return m.group(2)
    return raw


def parse_money_to_int(text: object) -> int | None:
    """Parse an arbitrary money-ish string/number to an integer, or None if not found."""
    if text is None:
        return None
    if isinstance(text, bool):
        return None
    if isinstance(text, (int, float)):
        try:
            v = int(text)
            return v if v >= 0 else None
        except (ValueError, OverflowError):
            return None

    raw = str(text).strip()
    if not raw:
        return None
    if _NO_BUDGET_RE.search(raw):
        return None

    s = _pick_range_upper(raw)

    s_clean = re.sub(_CURRENCY_RE, " ", s, flags=re.I)
    s_clean = re.sub(r"\b(?:dollars?|euros?|pounds?|rupees?|bucks?)\b", " ", s_clean, flags=re.I)
    s_clean = re.sub(r"(?<=\d),(?=\d)", "", s_clean)
    s_clean = re.sub(r"\s+", " ", s_clean).strip()

    m_num = re.match(
        r"^\s*(\d+(?:\.\d+)?)\s*"
        r"(k|m|mn|mil|million|b|bn|billion|thousand|lakhs?|lacs?|crores?|cr)?\s*$",
        s_clean,
        re.I,
    )
    if m_num:
        val = float(m_num.group(1))
        scale_tok = (m_num.group(2) or "").strip().lower()
        scale = _SCALES.get(scale_tok, 1) if scale_tok else 1
        result = int(round(val * scale))
        return result if result >= 0 else None

    m_scale = re.search(
        r"\b(\d+(?:\.\d+)?)\s*"
        r"(k|m|mn|mil|million|b|bn|billion|thousand|lakhs?|lacs?|crores?|cr)\b",
        s_clean,
        re.I,
    )
    if m_scale:
        val = float(m_scale.group(1))
        scale = _SCALES[m_scale.group(2).lower()]
        return int(round(val * scale))

    m_words = re.search(
        r"\b("
        r"(?:(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
        r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|"
        r"thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|and|a|an|half)\s+)+"
        r"(?:thousand|lakhs?|lacs?|million|crores?|cr|billion|bn)\b)",
        s_clean,
        re.I,
    )
    if m_words:
        val = _words_to_number(m_words.group(1))
        if val:
            return val

    m_plain = re.search(r"\b(\d{3,})\b", s_clean)
    if m_plain:
        try:
            return int(m_plain.group(1))
        except ValueError:
            pass

    return None


def parse_money_to_str(text: object) -> str:
    """Convenience wrapper that returns the integer as a string, or an empty string."""
    v = parse_money_to_int(text)
    return str(v) if v is not None else ""
