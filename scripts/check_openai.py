"""
scripts/check_openai.py — one tiny OpenAI call to confirm the API key works.

WHAT: Sends a very short prompt to the chat model (gpt-4o-mini by default) asking it to reply
      "Pehchaan is ready", then prints the result. It costs a fraction of a cent.
WHY:  Before Modules 3-9 depend on OpenAI (TTS, transcription, embeddings, LLM checks),
      we want to know right away if the key is missing, wrong, or out of credit,
      with a clear message instead of a long error trace.

Run from the project root:
    python scripts/check_openai.py
"""

import sys
from pathlib import Path

# Make the project root importable, so `from app.config import settings` works
# when this file runs as a script (Python otherwise only looks inside scripts/).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import openai  # noqa: E402  (import after the sys.path tweak on purpose)

from app.config import settings  # noqa: E402


def main() -> int:
    """Run the check. Returns a process exit code: 0 = success, 1 = failure."""

    # Step 1: make sure a key is configured at all. We only check that it exists.
    # We NEVER print the key itself.
    if settings.openai_api_key is None or not settings.openai_api_key.get_secret_value().strip():
        print("[ERROR] OPENAI_API_KEY is not set.")
        print("   Copy .env.example to .env and put your key in it, then run this again.")
        return 1

    # Step 2: create the OpenAI client. get_secret_value() unwraps the SecretStr.
    client = openai.OpenAI(api_key=settings.openai_api_key.get_secret_value())

    # Step 3: make the smallest useful call. max_tokens keeps the cost tiny,
    # and temperature=0 makes the reply predictable.
    try:
        response = client.chat.completions.create(
            model=settings.chat_model,
            messages=[{"role": "user", "content": "Reply with exactly: Pehchaan is ready"}],
            max_tokens=10,
            temperature=0,
        )
    # Step 4: catch the common failures and explain each one in plain words.
    except openai.AuthenticationError:
        print("[ERROR] The API key was rejected (authentication error). Check OPENAI_API_KEY in .env.")
        return 1
    except openai.RateLimitError:
        print("[ERROR] Rate limit or quota exceeded. Check billing/credits at platform.openai.com.")
        return 1
    except openai.NotFoundError:
        print(f"[ERROR] Model '{settings.chat_model}' was not found for this key. Check CHAT_MODEL.")
        return 1
    except openai.APIConnectionError:
        print("[ERROR] Could not reach OpenAI. Check your internet connection.")
        return 1
    except openai.OpenAIError as err:
        # Any other OpenAI error: show its type and message (they never contain the key).
        print(f"[ERROR] OpenAI error ({type(err).__name__}): {err}")
        return 1

    # Step 5: success. Show the model's reply and which model answered.
    reply = (response.choices[0].message.content or "").strip()
    print(f"[OK] OpenAI key works! Model '{response.model}' replied: {reply}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
