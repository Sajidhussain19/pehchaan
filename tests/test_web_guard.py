"""
tests/test_web_guard.py — the demo page is served, and the public-demo guards work (Module 10).

WHAT: - GET / returns the page; its CSS, JavaScript and icon load; the API still works next to it.
      - Rate limit: the N+1-th POST /api/process from one IP within the window gets 429 with a clear message.
      - Daily budget: when today's OpenAI spend would pass DAILY_BUDGET_USD, requests get 503; spend is recorded.
      - Demo key: if DEMO_KEY is set, changing requests need the X-Demo-Key header.
      - Origin lock: a POST from another website's page is refused (403); our own origin is fine.
WHY:  A public link to a paid API must not be abusable, and the page must load on stage.
      All tests use a temporary database and a fake OpenAI client: no network, no cost.
"""

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

import app.kb.loader as loader
import app.store.db as db
from app.api import guard
from app.api.routes import openai_client
from app.config import settings
from app.main import app
from tests.test_api import FakeOpenAI, wav_bytes

SENTENCE = {"text": "Remind me to call my doctor at 6 PM.", "book": "A"}


@pytest.fixture
def api(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "app.db")
    monkeypatch.setattr(loader, "RUNTIME_PREFS_DIR", tmp_path)
    monkeypatch.setattr(loader, "PREFERENCES_PATH", tmp_path / "preferences_default.json")
    guard.reset_rate_limits()
    app.dependency_overrides[openai_client] = lambda: FakeOpenAI()
    yield TestClient(app)
    app.dependency_overrides.clear()
    guard.reset_rate_limits()


# --- the page --------------------------------------------------------------------------------------------

def test_page_and_static_assets_load(api):
    page = api.get("/")
    assert page.status_code == 200 and "text/html" in page.headers["content-type"]
    html = page.text
    assert "Pehchaan" in html and 'src="app.js"' in html and 'href="style.css"' in html
    assert "Equal AI" not in html  # we are a layer, not their product: no borrowed branding
    for path, ctype in (("/app.js", "javascript"), ("/style.css", "text/css"), ("/favicon.svg", "image/svg+xml")):
        r = api.get(path)
        assert r.status_code == 200 and ctype in r.headers["content-type"], path
    assert "OPENAI" not in api.get("/app.js").text.upper().replace("OPENAI KEY", "")  # no key in the browser code
    assert api.get("/health").json()["status"] == "ok"  # the API still wins over the static mount
    assert api.get("/api/config").json()["demo_key_required"] is False


# --- rate limit ------------------------------------------------------------------------------------------

def test_rate_limit_per_ip(api, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_requests", 3)
    for _ in range(3):
        assert api.post("/api/process", data=SENTENCE).status_code == 200
    blocked = api.post("/api/process", data=SENTENCE)
    assert blocked.status_code == 429 and "Too many requests" in blocked.json()["detail"]
    assert "try again in" in blocked.json()["detail"]


def test_rate_limit_uses_forwarded_ip_only_behind_a_proxy(api, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_requests", 1)
    monkeypatch.setattr(settings, "trust_proxy", True)
    assert api.post("/api/process", data=SENTENCE, headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 200
    assert api.post("/api/process", data=SENTENCE, headers={"X-Forwarded-For": "2.2.2.2"}).status_code == 200
    assert api.post("/api/process", data=SENTENCE, headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 429
    # A visitor can't dodge the limit by sending a fake first address: CloudFront's own (last) entry counts.
    spoof = {"X-Forwarded-For": "9.9.9.9, 1.1.1.1"}
    assert api.post("/api/process", data=SENTENCE, headers=spoof).status_code == 429


# --- daily budget ----------------------------------------------------------------------------------------

def test_daily_budget_blocks_when_used_up(api, monkeypatch):
    monkeypatch.setattr(settings, "daily_budget_usd", 1.0)
    assert api.post("/api/process", data=SENTENCE).status_code == 200
    guard.record_spend(0.999)  # pretend the day's budget is almost gone
    r = api.post("/api/process", data=SENTENCE)
    assert r.status_code == 503 and "daily AI budget" in r.json()["detail"]


def test_spend_is_recorded_from_real_costs(api):
    before = guard.spent_today()
    files = {"file": ("mic.wav", wav_bytes(2.0), "audio/wav")}
    body = api.post("/api/process", data={"book": "A", "compare": "true"}, files=files).json()
    expected = body["cost_usd"] + body["baseline_cost_usd"]
    assert expected > 0 and guard.spent_today() == pytest.approx(before + expected)


# --- demo key and origin ---------------------------------------------------------------------------------

def test_demo_key_required_when_set(api, monkeypatch):
    monkeypatch.setattr(settings, "demo_key", SecretStr("open-sesame"))
    assert api.get("/api/config").json()["demo_key_required"] is True
    assert api.post("/api/process", data=SENTENCE).status_code == 401
    assert api.post("/api/process", data=SENTENCE, headers={"X-Demo-Key": "wrong"}).status_code == 401
    assert api.post("/api/process", data=SENTENCE, headers={"X-Demo-Key": "open-sesame"}).status_code == 200
    assert api.get("/api/clips").status_code == 200  # reading is still open


def test_requests_from_other_websites_are_refused(api, monkeypatch):
    evil = api.post("/api/process", data=SENTENCE, headers={"Origin": "https://evil.example"})
    assert evil.status_code == 403
    assert api.post("/api/process", data=SENTENCE, headers={"Origin": "http://testserver"}).status_code == 200
    monkeypatch.setattr(settings, "allowed_origins", "https://d123.cloudfront.net")
    ok = api.post("/api/process", data=SENTENCE, headers={"Origin": "https://d123.cloudfront.net"})
    assert ok.status_code == 200
