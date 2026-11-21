"""
tests/test_failures.py — what the live app does when OpenAI fails (timeout, 5xx, rate limit, no key).

WHAT: A fake OpenAI client that FAILS in each of those ways is plugged into the real API:
      - Pehchaan's LLM step fails  -> it ASKS with the top candidates ("AI unavailable — asked you instead"),
        never guesses, never crashes, and creates no reminder until the user answers.
      - the strong-AI comparison fails -> Pehchaan's answer still comes back; the card says why (no HTTP 500).
      - live speech-to-text fails -> HTTP 503 with a clear message; demo clips and typed text still work.
      - the OpenAI client has a 20 s timeout (the SDK default of 600 s could stall a demo for minutes).
WHY:  On stage the Wi-Fi or the API can fail. The safe behaviour must be tested, not hoped for.
"""

import functools
from types import SimpleNamespace

import httpx
import openai
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

import app.api.routes as routes
import app.kb.loader as loader
import app.store.db as db
from app.api.routes import openai_client
from app.main import app
from app.stt import transcribe as stt
from tests.test_api import wav_bytes

REQ = httpx.Request("POST", "https://api.openai.com/v1/x")
FAILURES = {
    "timeout": lambda: openai.APITimeoutError(request=REQ),
    "5xx": lambda: openai.InternalServerError("server error", response=httpx.Response(500, request=REQ), body=None),
    "rate_limit": lambda: openai.RateLimitError("slow down", response=httpx.Response(429, request=REQ), body=None),
    "no_key": lambda: RuntimeError("OPENAI_API_KEY is not set."),
}
NEEDS_LLM = "Call Aunt Johnny and ask if Matt's tuition is on this evening."  # Pehchaan's LLM step decides this


class FailingOpenAI:
    def __init__(self, make_error):
        self.make_error = make_error
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._fail))
        self.audio = SimpleNamespace(transcriptions=SimpleNamespace(create=self._fail))

    def _fail(self, **kwargs):
        raise self.make_error()


@pytest.fixture(params=list(FAILURES))
def api(request, tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "app.db")
    monkeypatch.setattr(loader, "RUNTIME_PREFS_DIR", tmp_path)
    # Speech-to-text retries with real waits (1+2+4 s); skip the waiting in tests.
    monkeypatch.setattr(routes, "transcribe", functools.partial(stt.transcribe, sleep=lambda s: None))
    app.dependency_overrides[openai_client] = lambda: FailingOpenAI(FAILURES[request.param])
    yield TestClient(app, raise_server_exceptions=False)  # like a real server: a crash would be an HTTP 500
    app.dependency_overrides.clear()


def test_llm_failure_asks_instead_of_guessing(api):
    r = api.post("/api/process", data={"text": NEEDS_LLM, "compare": "false"})
    assert r.status_code == 200
    body = r.json()
    assert body["decision"]["behaviour"] == "clarify" and body["ai_unavailable"] is True
    assert body["reminder"] is None  # nothing is done until the user answers
    assert body["pending"]["reason"].startswith("AI unavailable — asked you instead")
    assert len(body["pending"]["candidates"]) >= 1  # the top candidates are offered
    assert body["decision"]["action"]["target_entity_id"] is None  # never a guess


def test_comparison_failure_does_not_break_pehchaan(api):
    r = api.post("/api/process", data={"text": "Remind me to call my doctor at 6 PM.", "compare": "true"})
    assert r.status_code == 200
    body = r.json()
    assert body["baseline"] is None and body["baseline_error"].startswith("Strong AI unavailable")
    assert body["reminder"]["target_name"] == "Dr. Venkataramana"  # Pehchaan's answer still arrives
    assert len(api.get("/api/reminders").json()) == 1  # and no orphan reminders behind an error page


def test_speech_to_text_failure_is_a_clear_503(api):
    files = {"file": ("mic.wav", wav_bytes(2.0), "audio/wav")}
    r = api.post("/api/process", data={"compare": "false"}, files=files)
    assert r.status_code == 503
    assert "Speech-to-text is unavailable right now" in r.json()["detail"]
    assert "Demo clips and typed sentences still work" in r.json()["detail"]


def test_demo_clips_and_plain_text_still_work(api):
    clip = api.post("/api/process", data={"clip_id": "s104", "variant": "clean", "compare": "true"})
    assert clip.status_code == 200 and clip.json()["verdict"]["pehchaan"]["label"] == "✓ Correct"
    text = api.post("/api/process", data={"text": "Call my doctor, my tooth is paining.", "compare": "false"})
    assert text.status_code == 200 and text.json()["reminder"]["target_name"] == "Dr. Subramanian"


def test_openai_client_has_a_short_timeout(monkeypatch):
    monkeypatch.setattr(stt.settings, "openai_api_key", SecretStr("sk-test-not-real"))
    assert stt.get_client().timeout == 20.0


def test_page_uses_the_new_wording():
    js = TestClient(app).get("/app.js").text
    assert "Fast path · no LLM call needed" in js and "LLM reasoning used" in js
    assert "Decided on the fast path (no LLM call)" in js and "No AI call" not in js
