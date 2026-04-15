"""Clean deal `product` for HubSpot: strip trailing version labels into a separate fragment."""

from __future__ import annotations

import re


def clean_product_for_hubspot(product: str) -> tuple[str, str]:
    """
    Returns (product_label, version_fragment).

    Strips trailing patterns like "v2.1", "version 7.7", "(3.0)" from the product line
    so HubSpot shows a clean commercial name; version can be stored in `product_version`.
    """
    s = (product or "").strip()
    if not s:
        return "", ""
    version = ""
    # Trailing (v1.2.3) or v1.2.3
    m = re.search(r"(?i)\s*[\(]?\s*v?\s*(\d+\.\d+(?:\.\d+)?)\s*[\)]?\s*$", s)
    if m:
        version = m.group(1)
        s = s[: m.start()].strip().rstrip("-–—,;")
    # Trailing "version 7.7"
    m2 = re.search(r"(?i)\s+version\s+(\d+\.\d+(?:\.\d+)?)\s*$", s)
    if m2 and not version:
        version = m2.group(1)
        s = s[: m2.start()].strip().rstrip("-–—,;")
    # Phrase "map update version 7.7" as whole tail
    m3 = re.search(r"(?i)\s+(map\s+update\s+version\s+[\d.]+)\s*$", s)
    if m3:
        tail = m3.group(1)
        if not version:
            vm = re.search(r"([\d.]+)\s*$", tail)
            if vm:
                version = vm.group(1)
        s = s[: m3.start()].strip().rstrip("-–—,;")
    s = re.sub(r"\s+", " ", s).strip()
    return s, version


def extract_map_version_from_transcript(transcript: str) -> str:
    """
    Pull software/map version from raw transcript when the LLM moved it out of `product`
    (e.g. 'newest version ... is version 7.7').
    """
    t = (transcript or "").strip()
    if not t:
        return ""
    # Prefer explicit "version X.Y" (map / OEM context)
    for m in re.finditer(r"(?i)\bversion\s+(\d+\.\d+(?:\.\d+)?)\b", t):
        ver = m.group(1)
        # Avoid picking a calendar year when caller says "2012" without "version"
        if re.match(r"^20\d{2}$", ver):
            continue
        return ver
    return ""
