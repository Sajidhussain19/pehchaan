"""
app/stt/transcribe.py — turns one audio file into text with OpenAI speech-to-text.

WHAT: `transcribe(audio_path, prompt=None)` sends the audio to the transcription model and returns
      {text, model, latency_ms, cost_estimate_usd}. Short network hiccups (rate limits, timeouts,
      server errors) are retried with exponential backoff.
WHY:  This is baseline (a) (no prompt) and baseline (b) (prompt = name hints). The same function
      will later be the first step of the live Pehchaan pipeline, so latency and cost are measured
      from the start.
"""

import time
from functools import lru_cache
from pathlib import Path

import openai
import soundfile as sf

from app.config import settings

# Approximate public prices (US dollars), used only for cost ESTIMATES.
# Audio is billed per minute; the gpt-4o models also bill the prompt text as input tokens.
PRICE_PER_AUDIO_MINUTE = {
    "gpt-4o-mini-transcribe": 0.003,
    "gpt-4o-transcribe": 0.006,
    "whisper-1": 0.006,
}
PRICE_PER_PROMPT_TOKEN = {
    "gpt-4o-mini-transcribe": 1.25 / 1_000_000,
    "gpt-4o-transcribe": 2.50 / 1_000_000,
    "whisper-1": 0.0,
}
SUPPORTED_MODELS = tuple(PRICE_PER_AUDIO_MINUTE)

# Errors that usually go away if we simply wait and try again.
RETRYABLE_ERRORS = (
    openai.RateLimitError,
    openai.APIConnectionError,  # includes timeouts
    openai.InternalServerError,
)


@lru_cache(maxsize=1)
def get_client() -> openai.OpenAI:
    """One shared OpenAI client. max_retries=0 because we do our own, visible retry loop below."""
    if settings.openai_api_key is None:
        raise RuntimeError("OPENAI_API_KEY is not set. Add it to .env (see .env.example).")
    return openai.OpenAI(api_key=settings.openai_api_key.get_secret_value(), max_retries=0)


def audio_seconds(audio_path: Path) -> float:
    """Length of an audio file in seconds (read from the file header, no decoding needed)."""
    info = sf.info(str(audio_path))
    return info.frames / info.samplerate


def estimate_cost(seconds: float, model: str, prompt: str | None = None) -> float:
    """Estimated dollars for transcribing `seconds` of audio, plus the prompt's text tokens."""
    prompt_tokens = len(prompt) / 4 if prompt else 0  # ~4 characters per token for English text
    return seconds / 60 * PRICE_PER_AUDIO_MINUTE[model] + prompt_tokens * PRICE_PER_PROMPT_TOKEN[model]


def transcribe(
    audio_path: str | Path,
    prompt: str | None = None,
    model: str | None = None,
    client=None,
    max_attempts: int = 4,
    sleep=time.sleep,
) -> dict:
    """Transcribe one audio file.

    Args:
        audio_path: path to a WAV (or other supported) file.
        prompt: optional text that nudges the model (baseline (b) puts the name hints here).
        model: defaults to settings.transcription_model.
        client, sleep: can be replaced in tests, so tests never call the real API or really wait.

    Returns: {"text", "model", "latency_ms", "cost_estimate_usd"}
    """
    model = model or settings.transcription_model
    if model not in SUPPORTED_MODELS:
        raise ValueError(f"unsupported model {model!r}; choose one of {SUPPORTED_MODELS}")
    client = client or get_client()
    audio_path = Path(audio_path)

    for attempt in range(1, max_attempts + 1):
        try:
            start = time.perf_counter()
            with audio_path.open("rb") as audio_file:
                kwargs = {"model": model, "file": audio_file}
                if prompt:
                    kwargs["prompt"] = prompt
                response = client.audio.transcriptions.create(**kwargs)
            latency_ms = (time.perf_counter() - start) * 1000
            break
        except RETRYABLE_ERRORS:
            if attempt == max_attempts:
                raise
            # Exponential backoff: wait 1s, 2s, 4s... so a busy server gets breathing room.
            sleep(2 ** (attempt - 1))

    return {
        "text": response.text.strip(),
        "model": model,
        "latency_ms": round(latency_ms, 1),
        "cost_estimate_usd": round(estimate_cost(audio_seconds(audio_path), model, prompt), 6),
    }
