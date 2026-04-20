from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"
load_dotenv(_ENV_PATH)


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_PATH) if _ENV_PATH.is_file() else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI CRM Automation API"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    database_url: str | None = None

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]

    # --- Groq (OpenAI-compatible API at https://api.groq.com/openai/v1) ---
    groq_api_key: str | None = None
    groq_model: str = Field(
        default="llama-3.3-70b-versatile",
        description="Groq model id, e.g. llama-3.3-70b-versatile",
    )

    # Per-audio-file Groq call to label Whisper segments with Sales/Customer/names.
    # Default ON for accuracy: feeds speaker context into downstream Groq extraction
    # so "our budget is 50k" is correctly attributed to Sales vs Customer.
    # Costs ~2-4s per upload. Flip to false only when latency matters more than
    # attribution correctness (see WHISPER_PROFILE=fast).
    groq_label_speakers: bool = True

    # --- faster-whisper (local ASR) ---
    # Speed/accuracy profile. Applied lazily via `resolve_whisper_profile()` so
    # explicit WHISPER_MODEL/BEAM/FAST_DECODE env overrides always win.
    #   fast     : base  + beam=1      (~6% WER, fastest, dashboards/demos)
    #   balanced : small + beam=5      (~4% WER, production default)
    #   quality  : large-v3 + beam=5   (~3% WER, legal/compliance workloads)
    whisper_profile: str = Field(
        default="balanced",
        description="'fast' | 'balanced' | 'quality' — one-knob override for whisper_model/beam/fast_decode",
    )

    # Model size controls the speed/accuracy tradeoff.
    #   tiny / base         : fastest; WER ~6% on clean English
    #   small / medium      : balanced; WER ~4%
    #   large-v3 / large-v3-turbo : slowest; WER ~3%
    # Default `small` (balanced profile) — override via WHISPER_MODEL env.
    # Use an absolute path to a pre-downloaded CTranslate2 model directory to run
    # ASR with no Hugging Face Hub access at runtime (copy the folder from another
    # machine or mirror). Size names (small, base, …) may download from Hub once.
    whisper_model: str = "small"

    # ISO language hint; skips auto-detection (saves 1-3s per call).
    whisper_language: str = Field(default="en", description="Whisper language code, e.g. en")

    # Greedy decoding (beam=1) is 3-5x faster than beam=5 with ~1% more WER on
    # clean audio and 3-5% more on noisy audio. Default off in balanced profile.
    whisper_fast_decode: bool = False
    whisper_beam_size: int = 5

    # Voice Activity Detection prunes silent chunks before decoding (large speedup).
    whisper_vad: bool = True
    # Tighter silence threshold reduces false speech triggers on quiet noise.
    whisper_vad_min_silence_ms: int = 500

    # Drop Whisper segments whose average log-probability is below this threshold
    # (fraction on [0.0, 1.0] range maps to negative log-prob in ctranslate2).
    # Uses faster-whisper's `log_prob_threshold`. Empty string = library default (-1.0).
    whisper_log_prob_threshold: str = Field(
        default="-1.0",
        description="Reject segments with avg_logprob below this value (default -1.0; stricter = -0.5)",
    )

    # Device selection for faster-whisper / CTranslate2.
    #   auto -> CUDA when available, else CPU
    whisper_device: str = Field(default="auto", description="'auto', 'cpu', or 'cuda'")
    # Empty string lets the loader pick int8 (CPU) or float16 (CUDA).
    whisper_compute_type: str = Field(default="", description="int8 | int8_float16 | float16 | float32")

    # --- Extraction accuracy controls ---
    # Two-pass self-consistency on ambiguous fields (budget/intent/timeline/product_version).
    # Runs the facts extraction a second time at temperature=0.2 and reconciles
    # disagreements (keep agreed value; blank contested). ~+1 Groq call per ingest.
    extraction_self_consistency: bool = True

    # Evidence-grounded extraction: each extracted value must be supported by a
    # literal substring of the transcript. Values without evidence are blanked.
    # Eliminates hallucinated fields on noisy/ambiguous calls.
    extraction_require_evidence: bool = True

    # Feed speaker-labeled transcript ('[00:05] Sales: ...') into the extractor
    # instead of plain text. Requires groq_label_speakers=true for audio path.
    extraction_use_speaker_labels: bool = True

    # Fuzzy account matching: treat "Acme Corp", "Acme Inc.", "acme-corp" as the
    # same account when token-set similarity >= this threshold (0-100). Prevents
    # duplicate accounts from ASR casing/punctuation drift. Requires rapidfuzz.
    account_fuzzy_match_threshold: int = 88

    # SHA256-keyed in-process cache for identical re-ingests (Whisper + Groq).
    # Size = number of transcripts retained; 0 disables.
    extraction_cache_size: int = 64

    # Transcript display: "roles" keeps Sales/Customer labels; "speaker_ab" maps to A/B.
    transcript_speaker_labels: str = "roles"

    # --- OpenRouter (deal chat, e.g. Gemma) ---
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = Field(
        default="google/gemma-3-12b-it:free",
        description="OpenRouter model id for /agents/chat",
    )
    openrouter_timeout_sec: float = 25.0
    openrouter_referer: str = Field(
        default="http://localhost:5173",
        description="Optional Referer header for OpenRouter analytics",
    )

    # HubSpot private app token (used for deal sync).
    hubspot_api_key: str | None = None
    hubspot_pipeline_id: str = "default"
    hubspot_deal_stage_id: str = ""

    # --- Gmail (optional) ---
    gmail_send_enabled: bool = Field(
        default=False,
        description="When true, attempt real Gmail send once API client is configured",
    )
    gmail_oauth_client_id: str | None = None
    gmail_oauth_client_secret: str | None = None
    gmail_oauth_refresh_token: str | None = None

    # Fallback recipient when scheduled follow-up cannot infer an address from the record
    followup_default_email: str | None = Field(
        default=None,
        description="e.g. sales@company.com — used if participants/metadata have no email",
    )

    # Google OAuth (Gmail send + Calendar)
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str | None = None
    google_oauth_success_redirect: str = Field(
        default="http://localhost:5173/",
        description="Browser URL after OAuth callback (must match a registered redirect URI)",
    )

    # Cache window (seconds) for the /google/status probe so the TopBar pill
    # does not hit Google on every React re-render / dev-mode remount.
    google_status_cache_ttl_sec: float = 20.0

    # Response compression kicks in for payloads >= this threshold (bytes).
    gzip_min_size_bytes: int = 1024


_WHISPER_PROFILES: dict[str, dict[str, object]] = {
    "fast": {
        "whisper_model": "base",
        "whisper_fast_decode": True,
        "whisper_beam_size": 1,
        "groq_label_speakers": False,
        "extraction_self_consistency": False,
    },
    "balanced": {
        "whisper_model": "small",
        "whisper_fast_decode": False,
        "whisper_beam_size": 5,
        "groq_label_speakers": True,
        "extraction_self_consistency": True,
    },
    "quality": {
        "whisper_model": "large-v3",
        "whisper_fast_decode": False,
        "whisper_beam_size": 5,
        "groq_label_speakers": True,
        "extraction_self_consistency": True,
    },
}


def _apply_whisper_profile(s: Settings) -> Settings:
    """Apply WHISPER_PROFILE defaults, but only where the user did not set an explicit env var."""
    import os

    profile = (s.whisper_profile or "").strip().lower()
    if profile not in _WHISPER_PROFILES:
        return s
    preset = _WHISPER_PROFILES[profile]
    env_override = {
        "whisper_model": "WHISPER_MODEL",
        "whisper_fast_decode": "WHISPER_FAST_DECODE",
        "whisper_beam_size": "WHISPER_BEAM_SIZE",
        "groq_label_speakers": "GROQ_LABEL_SPEAKERS",
        "extraction_self_consistency": "EXTRACTION_SELF_CONSISTENCY",
    }
    for attr, value in preset.items():
        if os.environ.get(env_override[attr]) is None:
            setattr(s, attr, value)
    return s


@lru_cache
def get_settings() -> Settings:
    return _apply_whisper_profile(Settings())


settings = get_settings()
