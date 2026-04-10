"""Parse CRM budget strings to integers."""

import re


def _first_amount_in_fragment(text: str) -> int | None:
    """
    Extract the first monetary amount from a substring (digits, optional k/m suffix).

    Commas are treated as thousands separators; ₹/$/€ stripped.
    """
    t = (
        text.strip()
        .lower()
        .replace(",", "")
        .replace("₹", "")
        .replace("$", "")
        .replace("€", "")
        .replace("inr", "")
    )
    m = re.search(r"(\d+(?:\.\d+)?)\s*([km])?\b", t)
    if not m:
        return None
    try:
        val = float(m.group(1))
    except ValueError:
        return None
    suf = (m.group(2) or "").lower()
    mult = 1000 if suf == "k" else (1_000_000 if suf == "m" else 1)
    try:
        return max(0, int(round(val * mult)))
    except (ValueError, OverflowError):
        return None


def parse_budget_to_int(raw: str | None) -> int:
    """
    Parse stored budget strings (e.g. '80000', '50k', '$1,200', '₹75,000 to ₹90,000')
    to a non-negative int suitable for charts and totals.

    Ranges separated by '-', '–', '—', or the word 'to' are interpreted as min–max;
    the returned value is the **midpoint** (not digit-concatenation — the old bug).
    """
    if raw is None:
        return 0
    s = str(raw).strip()
    if not s:
        return 0

    work = s.lower()
    work = work.replace("₹", " ").replace("$", " ").replace("€", " ")
    # Treat "75 000 to 90 000" style
    work = re.sub(r"\s+to\s+", "-", work, flags=re.I)

    # Split on dashes that denote ranges (not minus signs inside a single number)
    parts = re.split(r"[\u2013\u2014\-]+", work)
    values: list[int] = []
    for p in parts:
        v = _first_amount_in_fragment(p)
        if v is not None:
            values.append(v)

    if len(values) >= 2:
        lo, hi = min(values), max(values)
        return (lo + hi) // 2

    if len(values) == 1:
        return values[0]

    # Legacy: single blob with no range separators (e.g. "80000" or "50k")
    legacy = s.lower().strip()
    if legacy.endswith("k"):
        mult = 1000
        legacy = legacy[:-1].strip()
    elif legacy.endswith("m"):
        mult = 1_000_000
        legacy = legacy[:-1].strip()
    else:
        mult = 1

    legacy = re.sub(r"[^\d.]", "", legacy.replace(",", ""))
    if not legacy:
        return 0
    try:
        return max(0, int(round(float(legacy) * mult)))
    except ValueError:
        return 0
