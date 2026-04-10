from dotenv import load_dotenv

# Load .env before Settings reads environment variables
load_dotenv()

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
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

    # --- Google Gemini (google-generativeai) ---
    # API credentials and model id must come from the environment / .env — do not
    # hardcode a model variant in application logic. Set GEMINI_MODEL to any model
    # id your project can use. Gemini 1.5 names are retired — prefer gemini-2.5-flash or gemini-2.5-pro.
    #
    # Quotas are enforced per Google Cloud / AI Studio project and per model: the same
    # API key may have different free-tier vs paid limits, and each model has its own
    # request and token quotas. If you see 429 errors, switch GEMINI_MODEL to another
    # model included in your plan, enable billing, or wait for quota reset — the app
    # does not pick a model for you.
    gemini_api_key: str | None = None
    gemini_model: str = Field(
        default="",
        description="Model id from GEMINI_MODEL (e.g. gemini-2.5-flash). Must be set to run extraction.",
    )

    # OpenAI Whisper (local); optional WHISPER_MODEL e.g. tiny, base, small, medium, large
    whisper_model: str = "base"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
