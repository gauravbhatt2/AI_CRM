"""Verify the full backend import graph loads cleanly after accuracy refactor."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.main  # noqa: F401,E402
from app.services.groq_extraction import _cache_key, clear_extraction_cache  # noqa: E402
from app.services.mapping_service import _best_fuzzy_account, _canon_account_name  # noqa: E402,F401
from app.core.config import settings  # noqa: E402

print("import OK")
print("profile:", settings.whisper_profile, "-> model:", settings.whisper_model, "beam:", settings.whisper_beam_size)
print("groq_label_speakers:", settings.groq_label_speakers)
print("extraction_self_consistency:", settings.extraction_self_consistency)
print("extraction_require_evidence:", settings.extraction_require_evidence)
print("account_fuzzy_match_threshold:", settings.account_fuzzy_match_threshold)
print("extraction_cache_size:", settings.extraction_cache_size)

print()
print("cache_key sample:", _cache_key("hello world")[:16], "...")
clear_extraction_cache()
print("clear_extraction_cache() OK")

for raw in ("Acme Corp, Inc.", "acme-corp inc", "Acme Incorporated", "ACME LTD"):
    print(f"canon({raw!r:30}) = {_canon_account_name(raw)!r}")
