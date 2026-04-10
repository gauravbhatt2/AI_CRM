from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
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

    # OpenAI Whisper (local); optional WHISPER_MODEL e.g. tiny, base, small, medium, large
    whisper_model: str = "base"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
