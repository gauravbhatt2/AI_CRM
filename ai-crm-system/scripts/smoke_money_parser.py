"""Smoke test for app.utils.money_parser — run from project root."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.utils.money_parser import parse_money_to_str  # noqa: E402

CASES: list[tuple[str, str]] = [
    ("seventy five thousand dollars", "75000"),
    ("5 lakh", "500000"),
    ("5 lakhs", "500000"),
    ("2 crore", "20000000"),
    ("1.5 crores", "15000000"),
    ("one and a half million", "1500000"),
    ("a million dollars", "1000000"),
    ("half a million", "500000"),
    ("$50,000", "50000"),
    ("$2.5M", "2500000"),
    ("between 40k and 60k", "60000"),
    ("no budget", ""),
    ("can't afford", ""),
    ("\u20b9 75000", "75000"),
    ("Rs. 2,00,000", "200000"),
    ("120k", "120000"),
    ("1.2 billion", "1200000000"),
]


def main() -> int:
    fails = 0
    for inp, expected in CASES:
        got = parse_money_to_str(inp)
        ok = got == expected
        status = "OK  " if ok else "FAIL"
        if not ok:
            fails += 1
        print(f"{status}  parse_money({inp!r}) -> {got!r} (want {expected!r})")
    print(f"\nTotal: {len(CASES)} cases, {fails} failures")
    return 0 if fails == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
