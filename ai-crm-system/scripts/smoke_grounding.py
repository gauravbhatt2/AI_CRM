"""Smoke test for app.services.extraction_grounding."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.extraction_grounding import ground_extracted_entities  # noqa: E402


def main() -> int:
    transcript = (
        "Hi, this is Alex from Acme Corp. We're evaluating you versus Salesforce. "
        "Our budget is 75000 dollars. Pain point is slow reporting."
    )
    entities = {
        "budget": "75000",
        "mentioned_company": "Acme Corp",
        "competitors": ["Salesforce", "Zoho"],
        "product": "Enterprise CRM",
        "pain_points": "slow reporting",
        "industry": "fintech",
    }
    grounded, rejected = ground_extracted_entities(entities, transcript)
    expected_rejections = {"product", "industry", "competitors"}
    actual_rejections = set(rejected.keys())
    missing = expected_rejections - actual_rejections
    extra = actual_rejections - expected_rejections

    print("INPUT:", entities)
    print("TRANSCRIPT:", transcript)
    print("GROUNDED:", grounded)
    print("REJECTED:", rejected)

    ok = True
    if grounded.get("budget") != "75000":
        print("FAIL: budget evidence lost")
        ok = False
    if "acme corp" not in grounded.get("mentioned_company", "").lower():
        print("FAIL: mentioned_company evidence lost")
        ok = False
    if "Zoho" in (grounded.get("competitors") or []):
        print("FAIL: Zoho should have been rejected (not in transcript)")
        ok = False
    if "Salesforce" not in (grounded.get("competitors") or []):
        print("FAIL: Salesforce should have been kept")
        ok = False

    if extra:
        print(f"FAIL: unexpected rejections {extra}")
        ok = False
    if missing:
        print(f"FAIL: expected to reject {missing} but did not")
        ok = False

    print("PASS" if ok else "FAIL")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
