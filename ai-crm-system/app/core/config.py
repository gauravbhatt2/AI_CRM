from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = directory that contains the `app` package (not process cwd).
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

    # PostgreSQL (SQLAlchemy); set DATABASE_URL in .env
    database_url: str | None = None

    # Browsers reject "*" when credentials=True; list Vite/React dev servers explicitly.
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]

    # --- Groq (OpenAI-compatible API at https://api.groq.com/openai/v1) ---
    # Set GROQ_API_KEY and GROQ_MODEL in .env — see https://console.groq.com/docs/models
    groq_api_key: str | None = None
    groq_model: str = Field(
        default="llama-3.3-70b-versatile",
        description="Groq model id, e.g. llama-3.3-70b-versatile, mixtral-8x7b-32768",
    )

    # Extra Groq call per audio file to label each Whisper segment (Sales / Customer / names).
    # Set GROQ_LABEL_SPEAKERS=false to disable and save quota.
    groq_label_speakers: bool = True

    # OpenAI Whisper (local). Use `turbo` (large-v3-turbo) for English: faster than `large` / `large-v3`.
    # Lighter dev option: tiny, base, small, medium.
    whisper_model: str = "turbo"
    # Passed to whisper.transcribe — skips auto language detection when set (English-only deployments).
    whisper_language: str = Field(default="en", description="Whisper language code, e.g. en")
    # Faster decode (beam_size=1); slightly lower quality. When false, uses whisper_beam_size.
    whisper_fast_decode: bool = False
    whisper_beam_size: int = 5

    # Transcript display: "roles" keeps Sales/Customer-style labels; "speaker_ab" maps to Speaker A / B.
    transcript_speaker_labels: str = "roles"

    # --- pyannote speaker diarization (optional; requires huggingface token + model license) ---
    huggingface_token: str | None = Field(
        default=None,
        description="Hugging Face token for pyannote models (accept license on model card first)",
    )
    pyannote_enabled: bool = Field(default=True, description="Run pyannote when token is set")
    pyannote_model_id: str = Field(
        default="pyannote/speaker-diarization-3.1",
        description="Hugging Face model id for diarization pipeline",
    )

    # --- OpenRouter (deal chat, e.g. Gemma) — requests-based; no transcript in prompt ---
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
    # Pipeline id (usually "default"). Stage id is portal-specific (numeric in many accounts).
    # Leave HUBSPOT_DEAL_STAGE_ID empty to auto-pick the first stage of that pipeline via the API.
    hubspot_pipeline_id: str = "default"
    hubspot_deal_stage_id: str = ""

    # --- Gmail (optional; demo uses mock send) ---
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

    # Google OAuth (Gmail send + Calendar) — mailNDcalendar integration
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str | None = None
    google_oauth_success_redirect: str = Field(
        default="http://localhost:5173/",
        description="Browser URL after OAuth callback (must match a registered redirect URI)",
    )

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug(cls, value):
        """Accept common deployment strings from shared shell environments."""
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production"}:
                return False
            if normalized in {"debug", "dev", "development"}:
                return True
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
