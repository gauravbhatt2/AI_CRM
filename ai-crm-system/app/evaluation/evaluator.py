"""
Compare unified pipeline output against fixed gold labels.

Run from `ai-crm-system` directory:
    python -m app.evaluation.evaluator

Requires GROQ_API_KEY and GROQ_MODEL for live scoring; without them, cases still
run heuristic fallback paths.
"""

from __future__ import annotations

import json
import sys
from typing import Any

# ---------------------------------------------------------------------------
# Gold cases: transcript + expected fields (subset; matching is case-insensitive
# for strings where noted).
# ---------------------------------------------------------------------------

EVAL_CASES: list[dict[str, Any]] = [
    {
        "id": "sales_budget",
        "transcript": (
            "Hi, this is Alex from Acme Corp. We're looking to buy your Enterprise CRM "
            "for about seventy five thousand dollars this quarter. Our main pain is manual "
            "reporting. Next step is a security review call next Tuesday."
        ),
        "expected": {
            "intent": "high",
            "mentioned_company": "Acme Corp",
            "interaction_type": "sales",
            "budget": "75000",
        },
    },
    {
        "id": "support_bug",
        "transcript": (
            "The integration is broken after the last update. We get a 500 error on login. "
            "Please fix urgently; nothing about pricing today."
        ),
        "expected": {
            "interaction_type": "support",
        },
    },
    {
        "id": "complaint",
        "transcript": (
            "This is unacceptable. We want to cancel immediately and escalate to legal "
            "if we do not get a refund."
        ),
        "expected": {
            "interaction_type": "complaint",
            "risk_level": "high",
        },
    },
    {
        "id": "inquiry_only",
        "transcript": (
            "Just calling to learn whether you offer API access for small teams. No timeline yet."
        ),
        "expected": {
            "interaction_type": "inquiry",
        },
    },
    {
        "id": "competitor_timeline",
        "transcript": (
            "We're evaluating you versus Salesforce for rollout in Q3. Budget is around 120k. "
            "Ship the hardware tomorrow is not the decision timeline \u2014 Q3 is when we decide."
        ),
        "expected": {
            "competitors": ["Salesforce"],
            "intent": "medium",
            "budget": "120000",
        },
    },
    {
        "id": "budget_indian_lakh",
        "transcript": (
            "Hi, Priya here from Flipwave Retail. We have an approved budget of 5 lakh rupees "
            "for the quarter and plan to roll out nationally once finance signs the PO."
        ),
        "expected": {
            "budget": "500000",
            "mentioned_company": "Flipwave Retail",
            "intent": "high",
        },
    },
    {
        "id": "budget_crore",
        "transcript": (
            "Our parent group has earmarked 2 crore for this initiative, and we want to close "
            "before the end of Q1. We've compared you with Salesforce and Zoho."
        ),
        "expected": {
            "budget": "20000000",
            "competitors": ["Salesforce", "Zoho"],
        },
    },
    {
        "id": "budget_million_words",
        "transcript": (
            "We want to commit one and a half million dollars in the first year. "
            "Legal is reviewing the MSA right now; timeline is Q2 go-live."
        ),
        "expected": {
            "budget": "1500000",
            "intent": "high",
        },
    },
    {
        "id": "budget_range",
        "transcript": (
            "Our budget is somewhere between 40k and 60k depending on the seat count. "
            "We need the deal closed in the next two months."
        ),
        "expected": {
            "budget": "60000",
        },
    },
    {
        "id": "no_budget_low_intent",
        "transcript": (
            "Honestly, we have no budget this year and we're just exploring options. "
            "We'll circle back next fiscal maybe."
        ),
        "expected": {
            "intent": "low",
            "interaction_type": "inquiry",
        },
    },
    {
        "id": "procurement_stage_negotiation",
        "transcript": (
            "Proposal received, legal is redlining the MSA, and procurement has asked "
            "for a 10% discount. We are in active contract negotiation."
        ),
        "expected": {
            "procurement_stage": "negotiation",
            "intent": "high",
        },
    },
    {
        "id": "pilot_scope",
        "transcript": (
            "Let's start with a 90-day pilot for the APAC region with five seats. "
            "If that works we will roll out company-wide in Q4."
        ),
        "expected": {
            "implementation_scope": "pilot",
            "intent": "medium",
        },
    },
    {
        "id": "budget_owner",
        "transcript": (
            "CFO Ravi Menon owns the budget. He wants ROI within 12 months. "
            "Reporting time is our biggest pain today."
        ),
        "expected": {
            "budget_owner": "Ravi Menon",
            "pain_points": "reporting",
        },
    },
    {
        "id": "speaker_attribution",
        "transcript": (
            "[00:00] Sales: Thank you for calling. How can I help?\n"
            "[00:04] Customer: I'm Maya from Bluebird Labs. Our budget is 30k for a new CRM.\n"
            "[00:12] Sales: We can do that. Timeline?\n"
            "[00:15] Customer: We need to decide within two weeks."
        ),
        "expected": {
            "budget": "30000",
            "mentioned_company": "Bluebird Labs",
            "intent": "high",
        },
    },
    {
        "id": "urgency_risk",
        "transcript": (
            "If we can't resolve this by Friday we'll have to pull the contract. "
            "Our COO is copied on this escalation."
        ),
        "expected": {
            "risk_level": "high",
            "interaction_type": "complaint",
        },
    },
]

_EXTRACTION_KEYS = (
    "budget",
    "intent",
    "timeline",
    "product",
    "mentioned_company",
    "competitors",
    "interaction_type",
)
_AI_KEYS = ("interaction_type", "deal_score", "risk_level", "risk_reason", "summary", "next_action", "tags")


def _norm_str(v: Any) -> str:
    return str(v or "").strip().lower()


def _field_match(predicted: Any, expected: Any, *, field: str) -> bool:
    if field == "competitors":
        if not isinstance(expected, list):
            return False
        pred = predicted if isinstance(predicted, list) else []
        exp_l = [str(x).strip().lower() for x in expected if str(x).strip()]
        pred_l = [str(x).strip().lower() for x in pred if str(x).strip()]
        return all(any(e in p or p in e for p in pred_l) for e in exp_l) if exp_l else True
    if field in ("mentioned_company", "budget_owner", "pain_points", "procurement_stage", "implementation_scope"):
        pe, ee = _norm_str(predicted), _norm_str(expected)
        if not ee:
            return True
        return ee in pe or pe in ee
    if field == "budget":
        return _norm_str(predicted) == _norm_str(expected)
    if field == "deal_score":
        try:
            return abs(int(predicted) - int(expected)) <= 15
        except (TypeError, ValueError):
            return False
    return _norm_str(predicted) == _norm_str(expected)


def _run_case(case: dict[str, Any]) -> dict[str, Any]:
    from app.services.groq_extraction import run_unified_extraction

    transcript = case["transcript"]
    gold = case["expected"]
    entities, ai = run_unified_extraction(transcript)
    merged: dict[str, Any] = {**entities, **ai}
    per_field: dict[str, bool] = {}
    for field, exp in gold.items():
        per_field[field] = _field_match(merged.get(field), exp, field=field)
    correct = sum(1 for v in per_field.values() if v)
    total = len(per_field)
    return {
        "id": case["id"],
        "per_field": per_field,
        "case_accuracy": (correct / total * 100.0) if total else 100.0,
        "predicted_sample": {k: merged.get(k) for k in gold},
    }


def run_evaluation() -> dict[str, Any]:
    field_hits: dict[str, list[bool]] = {}
    case_results: list[dict[str, Any]] = []
    for case in EVAL_CASES:
        r = _run_case(case)
        case_results.append(r)
        for fname, ok in r["per_field"].items():
            field_hits.setdefault(fname, []).append(ok)

    field_accuracy: dict[str, float] = {}
    for fname, hits in field_hits.items():
        field_accuracy[fname] = round(sum(hits) / len(hits) * 100.0, 2) if hits else 0.0

    all_hits = [h for hits in field_hits.values() for h in hits]
    accuracy_score = round(sum(all_hits) / len(all_hits) * 100.0, 2) if all_hits else 0.0

    return {
        "accuracy_score": accuracy_score,
        "field_accuracy": field_accuracy,
        "cases": case_results,
        "schema_note": f"Extraction keys sampled: {_EXTRACTION_KEYS}; AI keys: {_AI_KEYS}",
    }


CI_ACCURACY_THRESHOLD = 75.0


def main() -> None:
    report = run_evaluation()
    print(json.dumps(report, indent=2))
    # CI gate matches the BRD §7 operational KPI: >=75% field-match accuracy.
    # Tune via `python -m app.evaluation.evaluator --gate 85` if you want stricter.
    gate = CI_ACCURACY_THRESHOLD
    for i, arg in enumerate(sys.argv):
        if arg == "--gate" and i + 1 < len(sys.argv):
            try:
                gate = float(sys.argv[i + 1])
            except ValueError:
                pass
    if report["accuracy_score"] < gate and len(EVAL_CASES) >= 3:
        print(
            f"FAIL: accuracy_score {report['accuracy_score']:.2f} < gate {gate:.2f}",
            file=sys.stderr,
        )
        sys.exit(2)
    print(f"PASS: accuracy_score {report['accuracy_score']:.2f} >= gate {gate:.2f}")


if __name__ == "__main__":
    main()
