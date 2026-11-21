"""
app/config.py — central settings for Pehchaan.

WHAT: Reads configuration (API key, model names) from environment variables or a `.env` file
      and exposes it as one typed `settings` object.
WHY:  Secrets must never be hard-coded in the source. Keeping every setting in one place
      also lets us swap models later (e.g. a different transcription model) without
      touching the rest of the code.

Usage anywhere in the project:
    from app.config import settings
    settings.chat_model   # -> "gpt-4o-mini"
"""

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# The project root is the folder one level above `app/`.
# We build the .env path from it, so loading works no matter which folder
# you start Python from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """All Pehchaan settings. Each field can be overridden by an env variable of the same name.

    Example: the field `chat_model` reads the env variable CHAT_MODEL.
    The match is case-insensitive.
    """

    # --- Secrets ---
    # SecretStr hides the value when printed or logged (it shows '**********'),
    # so the key can't leak into a log by accident.
    # It is Optional (None by default) so the server and tests still start
    # without a key. Only the scripts that call OpenAI need it.
    openai_api_key: SecretStr | None = None
    # Hugging Face access token, only needed to download the gated real-speech sample
    # (AI4Bharat Svarah). Create one at https://huggingface.co/settings/tokens.
    hf_token: SecretStr | None = None

    # --- Model names (sensible defaults, change them in .env if needed) ---
    # Speech-to-text model used for transcription (Module 4).
    transcription_model: str = "gpt-4o-transcribe"
    # Small, cheap, fast chat model for LLM checks and action extraction.
    chat_model: str = "gpt-4o-mini"
    # Embedding model for semantic matching (Module 7).
    embedding_model: str = "text-embedding-3-small"
    # Text-to-speech model for generating test audio (Module 3). It accepts an
    # "instructions" prompt (accent, pace). If it is unavailable on the account, we fall back
    # to the older tts-1 model, which has no instructions but always works.
    tts_model: str = "gpt-4o-mini-tts"
    tts_fallback_model: str = "tts-1"

    # --- App info ---
    project_name: str = "Pehchaan"

    # Tell pydantic-settings where the .env file is and how to read it.
    # extra="ignore": if .env has variables we don't define here, skip them quietly.
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Create one shared instance at import time. Every module imports this same object.
settings = Settings()
