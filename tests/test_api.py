"""
tests/test_api.py — end-to-end tests of the Module 9 API, with a FAKE OpenAI client (no network, $0).

WHAT: Drives the real FastAPI app through TestClient:
      - text -> Pehchaan -> a stored reminder (with heard -> resolved -> confidence -> reason)
      - the learning-with-consent loop on book B: ambiguous -> pending question -> "this time" (nothing learned)
        -> ask again -> "always" (preference saved) -> the same sentence now resolves automatically
      - contact books A vs B give different outcomes for "Remind me to call my doctor at six"
      - compare=true runs baseline (c) on the same transcript (faked) and stores nothing for it
      - audio: a clip goes through, an uploaded WAV goes through the (faked) speech-to-text
      - safety: upload size/type/length limits, path traversal blocked, bad ids rejected
WHY:  These are the promises the demo makes on stage. Every test uses a temporary database and
      temporary preference files, so it never touches the real demo state.
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock
import io
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4
import json
from types import SimpleNamespace

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

import app.kb.loader as loader
import app.store.db as db
from app.api.routes import openai_client
from app.main import app

DOCTOR_SENTENCE = "Remind me to call my doctor at six."


class FakeOpenAI:
    """Stands in for openai.OpenAI. Records every call. Speech-to-text returns `heard`; chat calls return a
    'keep' answer (Pehchaan's LLM fallback) or a fixed decision (baseline (c), schema name 'decision')."""

    def __init__(self, heard="Remind me to call my doctor at six."):
        self.calls, self.heard = [], heard
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._chat))
        self.audio = SimpleNamespace(transcriptions=SimpleNamespace(create=self._stt))

    def _stt(self, **kwargs):
        self.calls.append(("stt", kwargs["model"]))
        return SimpleNamespace(text=self.heard)

    def _chat(self, **kwargs):
        name = kwargs["response_format"]["json_schema"]["name"]
        self.calls.append(("chat", name))
        if name == "decision":  # baseline (c): pretends to guess the family doctor
            answer = {"output_transcript": "Remind me to call Dr. Venkataramana at six.", "behaviour": "resolve",
                      "entities": [{"heard_text": "my doctor", "resolved_entity_id": "person_001", "confidence": 0.9,
                                    "reason": "default doctor"}],
                      "clarify_candidates": [], "action": {"type": "remind", "target_entity_id": "person_001",
                                                           "place_entity_id": None, "time": None,
                                                           "raw_time_text": "at six"}}
        else:  # Pehchaan's small fallback: keep every unsure span
            answer = {"decisions": [{"phrase": 0, "choice": "keep", "reason": "not sure"}]}
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(answer)))],
                               usage=SimpleNamespace(prompt_tokens=500, completion_tokens=50, prompt_tokens_details=None))


def mock_live_stt(monkeypatch, fake):
    from app.stt import transcribe as stt

    create = AsyncMock(side_effect=fake.audio.transcriptions.create)

    @asynccontextmanager
    async def client():
        yield SimpleNamespace(audio=SimpleNamespace(transcriptions=SimpleNamespace(create=create)))

    monkeypatch.setattr(stt, "_live_client", client)
    monkeypatch.setattr(stt, "LIVE_STT_BACKOFF", 0)
    return create


@pytest.fixture
def fake():
    return FakeOpenAI()


@pytest.fixture
def api(tmp_path, monkeypatch, fake, visitor_headers):
    """A TestClient with a temporary database, temporary preference files and the fake OpenAI client."""
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "app.db")
    monkeypatch.setattr(loader, "RUNTIME_PREFS_DIR", tmp_path)
    monkeypatch.setattr(loader, "PREFERENCES_PATH", tmp_path / "preferences_default.json")
    mock_live_stt(monkeypatch, fake)
    app.dependency_overrides[openai_client] = lambda: fake
    yield TestClient(app, headers=visitor_headers)
    app.dependency_overrides.clear()


def process(api, **form):
    return api.post("/api/process", data={k: str(v).lower() if isinstance(v, bool) else v for k, v in form.items()})


def wav_bytes(seconds: float) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, np.zeros(int(16000 * seconds), dtype="float32"), 16000, format="WAV")
    return buf.getvalue()


# --- text -> reminder ------------------------------------------------------------------------------------

def test_text_creates_a_stored_reminder_with_heard_and_reason(api, fake):
    r = process(api, text="Call my doctor, my tooth is paining.", book="default")
    assert r.status_code == 200, r.text
    body = r.json()
    rem = body["reminder"]
    assert rem["target_entity_id"] == "person_028" and rem["target_name"] == "Dr. Subramanian"
    assert rem["target_role"] == "dentist" and rem["resolution"] == "auto" and rem["status"] == "created"
    assert rem["heard_transcript"] == "Call my doctor, my tooth is paining."
    assert rem["entities"][0]["reason"].startswith("resolve: clue 'tooth'")  # heard -> resolved -> reason kept
    span = body["spans"][0]
    assert span["heard_text"] == "my doctor" and span["resolved_name"] == "Dr. Subramanian"
    assert body["heard_transcript"][span["heard_start"]:span["heard_end"]] == "my doctor"
    assert body["used_llm"] is False and body["cost_usd"] == 0 and not fake.calls  # no OpenAI call at all
    assert set(body["timings"]) >= {"stt_ms", "pehchaan_ms", "baseline_ms", "total_ms"}
    # The reminder is REAL: it can be listed and opened again.
    assert api.get(f"/api/reminders/{rem['id']}").json()["target_name"] == "Dr. Subramanian"
    assert [x["id"] for x in api.get("/api/reminders").json()] == [rem["id"]]


def test_no_reminder_without_a_request(api):
    body = process(api, text="The cook at the polling booth said lunch is ready.").json()
    assert body["reminder"] is None and body["pending"] is None and body["decision"]["action"]["type"] == "none"


# --- contact books ---------------------------------------------------------------------------------------

def test_books_A_and_B_give_different_answers_for_the_same_sentence(api):
    a = process(api, text=DOCTOR_SENTENCE, book="A").json()
    b = process(api, text=DOCTOR_SENTENCE, book="B").json()
    assert a["reminder"]["target_name"] == "Dr. Venkataramana" and a["pending"] is None  # one doctor: clear
    assert b["reminder"] is None and b["decision"]["behaviour"] == "clarify"  # two doctors, no default: ask
    assert {c["name"] for c in b["pending"]["candidates"]} == {"Dr. Venkataramana", "Dr. Subramanian"}
    assert all(c["role"] for c in b["pending"]["candidates"])  # each candidate shows a role
    assert [x["book"] for x in api.get("/api/books").json()] == ["default", "A", "B"]


def test_unknown_book_is_rejected(api):
    assert process(api, text=DOCTOR_SENTENCE, book="Z").status_code == 404


# --- clarify with consent + learning ---------------------------------------------------------------------

def test_clarify_this_time_then_always_then_automatic(api):
    # 1. Book B asks.
    first = process(api, text=DOCTOR_SENTENCE, book="B").json()["pending"]
    assert first["phrase"] == "my doctor" and len(first["buttons"]) == 4

    # 2. "Use Dr. Subramanian this time": a reminder, but NOTHING is learned.
    r = api.post(f"/api/clarify/{first['id']}", json={"entity_id": "person_028", "remember": "this_time"}).json()
    assert r["reminder"]["target_name"] == "Dr. Subramanian"
    assert r["reminder"]["resolution"] == "clarified_this_time" and r["saved_preference"] is None
    again = process(api, text=DOCTOR_SENTENCE, book="B").json()
    assert again["decision"]["behaviour"] == "clarify"  # still asks: consent was only for this time

    # 3. "Always use Dr. Subramanian for 'my doctor'": saved for book B.
    r = api.post(f"/api/clarify/{again['pending']['id']}", json={"entity_id": "person_028", "remember": "always"}).json()
    assert r["reminder"]["resolution"] == "clarified_always"
    assert r["saved_preference"]["phrase_pattern"] == "my doctor"

    # 4. Next time: resolved automatically from the learned preference, no question.
    auto = process(api, text=DOCTOR_SENTENCE, book="B").json()
    assert auto["pending"] is None and auto["reminder"]["target_name"] == "Dr. Subramanian"
    assert auto["reminder"]["resolution"] == "preference"
    assert (auto["decision_source"], auto["latency_scope"]) == ("live", "end to end")
    stored = api.get(f"/api/reminders/{auto['reminder']['id']}").json()["entities"][0]
    assert (stored["name"], stored["role"], stored["method"]) == ("Dr. Subramanian", "dentist", "learned preference")
    assert "you told me" in auto["spans"][0]["reason"]

    # 5. The preference belongs to book B only; book A is unaffected. Reset brings the question back.
    assert process(api, text=DOCTOR_SENTENCE, book="A").json()["reminder"]["target_name"] == "Dr. Venkataramana"
    assert api.post("/api/preferences/reset?book=B").json()["removed"] == 1
    assert process(api, text=DOCTOR_SENTENCE, book="B").json()["decision"]["behaviour"] == "clarify"


def test_time_and_place_survive_the_clarify_round_trip(api):
    # The answer re-runs the same pipeline, so the reminder gets its time by the same rules as any other.
    # ("at six" alone has no time: 6 AM or 6 PM is ambiguous, and Pehchaan never guesses.)
    pid = process(api, text="Remind me to call my doctor at 6 PM.", book="B").json()["pending"]["id"]
    rem = api.post(f"/api/clarify/{pid}", json={"entity_id": "person_001", "remember": "this_time"}).json()["reminder"]
    assert rem["target_name"] == "Dr. Venkataramana" and rem["time"] == "18:00"


def test_clarify_rejects_bad_answers(api):
    pid = process(api, text=DOCTOR_SENTENCE, book="B").json()["pending"]["id"]
    assert api.post(f"/api/clarify/{pid}", json={"entity_id": "person_130", "remember": "always"}).status_code == 400
    assert api.post(f"/api/clarify/{pid}", json={"entity_id": "person_028", "remember": "forever"}).status_code == 422
    assert api.post("/api/clarify/0123456789abcdef", json={"entity_id": "person_028",
                                                           "remember": "always"}).status_code == 404
    assert api.post(f"/api/clarify/{pid}", json={"entity_id": "person_028", "remember": "this_time"}).status_code == 200
    # Answering twice is refused.
    assert api.post(f"/api/clarify/{pid}", json={"entity_id": "person_028", "remember": "this_time"}).status_code == 409


# --- compare with baseline (c) ---------------------------------------------------------------------------

def test_compare_runs_baseline_c_side_by_side_without_storing_it(api, fake):
    body = process(api, text=DOCTOR_SENTENCE, book="B", compare=True).json()
    assert body["baseline"]["action"]["target_entity_id"] == "person_001"  # (c) guesses
    assert body["decision"]["behaviour"] == "clarify"  # Pehchaan asks
    assert ("chat", "decision") in fake.calls and body["timings"]["baseline_ms"] is not None
    assert api.get("/api/reminders").json() == []  # the baseline's answer is never stored


# --- audio -----------------------------------------------------------------------------------------------

def test_clip_uses_the_saved_transcript_and_serves_audio(api, fake):
    body = process(api, clip_id="s140", variant="clean", book="default").json()
    assert body["decision_source"] == "saved evaluation replay" and body["latency_scope"] == "decision only"
    assert body["names"][body["decision"]["action"]["target_entity_id"]]["name"] == "Dr. Subramanian"
    assert body["reminder"] is None and body["pending"] is None
    assert api.get("/api/reminders").json() == []
    assert not fake.calls
    assert api.get("/audio/phone/s140.wav").headers["content-type"] == "audio/wav"


@pytest.mark.parametrize("variant", ["clean", "phone"])
def test_replay_uses_saved_output_and_timing_without_live_decisions(api, fake, monkeypatch, variant):
    from app.api import flow
    from app.eval.runs import load_decision_objects

    monkeypatch.setattr(flow, "_decide", lambda *args, **kwargs: pytest.fail("replay invoked a live decision"))
    body = process(api, clip_id="s090", variant=variant, compare=True).json()
    saved = load_decision_objects("pehchaan", variant, "v2")["s090"]
    assert body["v1_output"] == load_decision_objects("pehchaan", variant, "v1")["s090"].output_transcript
    assert body["decision"] == saved.model_dump()
    assert body["timings"]["pehchaan_ms"] == saved.latency_ms
    assert body["cost_usd"] == 0 and not fake.calls


def test_live_clip_override_previews_without_storing(api, fake):
    body = process(api, clip_id="s140", live_stt=True).json()
    assert (body["decision_source"], body["latency_scope"]) == ("live", "end to end")
    assert body["decision"]["action"]["type"] == "remind" and body["reminder"] is None
    assert fake.calls and api.get("/api/reminders").json() == []


def test_replayed_question_has_candidates_without_pending_item(api):
    replay = process(api, clip_id="s101").json()
    assert replay["pending"] is None and replay["spans"][0]["close_match_count"] == 3
    assert replay["v1_output"] is None
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM pending").fetchone()[0] == 0
    live = process(api, book="B", text=DOCTOR_SENTENCE).json()
    assert live["spans"][0]["close_match_count"] == len(live["pending"]["candidates"]) == 2


def test_uploaded_wav_goes_through_speech_to_text(api, fake):
    files = {"file": ("mic.wav", wav_bytes(2.0), "audio/wav")}
    body = api.post("/api/process", data={"book": "A"}, files=files).json()
    assert ("stt", "gpt-4o-mini-transcribe") in fake.calls
    assert body["heard_transcript"] == DOCTOR_SENTENCE and body["reminder"]["target_name"] == "Dr. Venkataramana"
    assert body["stt_source"].startswith("live") and body["cost_usd"] > 0


def test_upload_validation(api):
    def send(name, data, ctype="audio/wav"):
        return api.post("/api/process", data={"book": "A"}, files={"file": (name, data, ctype)})

    assert send("mic.wav", wav_bytes(31.0)).status_code == 400  # longer than 30 s
    assert "30 s" in send("mic.wav", wav_bytes(31.0)).json()["detail"]
    assert send("big.wav", b"RIFF" + b"\0" * (5 * 1024 * 1024 + 10)).status_code == 413  # over 5 MB
    assert send("notes.txt", b"hello, this is not audio", "text/plain").status_code == 415
    assert send("fake.mp3", wav_bytes(1.0)).status_code == 415  # name and content disagree
    assert send("mic.webm", b"\x1a\x45\xdf\xa3" + b"\0" * 1_100_000, "audio/webm").status_code == 400  # > ~30 s
    assert send("empty.wav", b"").status_code == 400
    both = api.post("/api/process", data={"text": "hi", "clip_id": "s001"})
    assert both.status_code == 422  # exactly one input


def test_path_traversal_and_bad_clip_ids_are_blocked(api):
    for url in ("/audio/clean/..%2F..%2F.env.wav", "/audio/clean/s999.wav", "/audio/secret/s001.wav",
                "/audio/real/s001.wav", "/audio/clean/%2e%2e.wav", "/audio/../.env"):
        assert api.get(url).status_code in (404, 422), url
    assert process(api, clip_id="../.env", variant="clean").status_code == 404


def test_metrics_and_clips_and_reset(api):
    m = api.get("/api/metrics").json()
    assert "held-out" in m["label"].lower() and set(m["overall"]) == {"c", "pehchaan"}
    assert m["overall"]["pehchaan"]["wrong_target_rate"]["total"] > 0  # raw counts, not just a percentage
    clips = api.get("/api/clips").json()
    assert clips[0]["group"].startswith("demo") or clips[0]["group"].startswith("Original")
    assert any(c["group"] == "Dev clips" for c in clips)
    process(api, text=DOCTOR_SENTENCE, book="A")
    assert api.delete("/api/reminders").json() == {"deleted": 1} and api.get("/api/reminders").json() == []


def test_rehearsed_clips_come_first_and_are_labelled_honestly(api):
    # The presenter rehearsed with s104, s140, s067, s090 (original test set). Since v2 they are "seen".
    clips = api.get("/api/clips").json()
    assert [c["clip_id"] for c in clips[:4]] == ["s104", "s140", "s067", "s090"]
    assert all(c["group"] == "Original test set (seen before v2)" for c in clips[:4])
    assert clips[3]["label"] in ("v1 failure — fixed in v2", "Known failure")  # computed from saved v2 results
    assert [c["clip_id"] for c in clips].count("s101") == 1
    assert clips[4]["clip_id"] == "s101" and clips[4]["group"] == "Dev set (used for tuning)"
    assert clips[4]["label"] == "near-identical names — Harshit or Harshil? (best on Phone audio)"
    assert [c["clip_id"] for c in clips[5:11]] == ["s202", "s208", "s203", "s199", "s206", "s185"]
    assert clips[10]["label"] == "Known failure (v2)"


def test_clip_verdict_uses_the_saved_v2_decision(api, fake):
    body = process(api, clip_id="s104", variant="clean", compare=True).json()
    assert body["verdict"]["pehchaan"]["label"] == "✓ Correct"  # asks Rohit Chaturvedi or Rohith Reddy
    assert body["verdict"]["baseline"]["label"] == "✗ Wrong target"  # (c)'s saved answer guessed
    assert body["decision_source"] == body["baseline_source"] == "saved evaluation replay"
    assert not fake.calls  # saved transcript + saved (c) + cached LLM answers: no API call at all


def test_visitor_owns_reminders_and_questions(api):
    other = {"X-Visitor-Id": str(uuid4())}
    mine = process(api, text=DOCTOR_SENTENCE, book="A").json()["reminder"]["id"]
    question = process(api, text=DOCTOR_SENTENCE, book="B").json()["pending"]["id"]
    choice = {"entity_id": "person_028", "remember": "always"}
    assert api.get("/api/reminders", headers=other).json() == []
    assert api.get(f"/api/reminders/{mine}", headers=other).status_code == 404
    assert api.post(f"/api/clarify/{question}", headers=other, json=choice).status_code == 404
    assert api.post(f"/api/clarify/{question}", json=choice).status_code == 200
    # Learning is still shared within a book, while the resulting reminder belongs to its caller.
    learned = api.post("/api/process", headers=other, data={"text": DOCTOR_SENTENCE, "book": "B"}).json()
    assert learned["reminder"]["resolution"] == "preference"
    assert api.delete("/api/reminders", headers=other).json() == {"deleted": 1}
    assert len(api.get("/api/reminders").json()) == 2


@pytest.mark.parametrize("header", [None, "invalid"])
def test_private_endpoints_require_valid_visitor(api, header):
    del api.headers["X-Visitor-Id"]
    if header is not None:
        api.headers["X-Visitor-Id"] = header
    for method, url, kwargs in [
        ("GET", "/api/reminders", {}), ("GET", "/api/reminders/1", {}), ("DELETE", "/api/reminders", {}),
        ("POST", "/api/clarify/0123456789abcdef", {"json": {"entity_id": "person_028", "remember": "always"}}),
        ("POST", "/api/process", {"data": {"text": DOCTOR_SENTENCE}}),
    ]:
        response = api.request(method, url, **kwargs)
        assert response.status_code == 400 and "X-Visitor-Id" in response.json()["detail"]
    for path in ("/", "/api/clips", "/api/metrics"):
        assert api.get(path).status_code == 200


def test_upgrade_preserves_and_hides_unowned_legacy_rows(api):
    with sqlite3.connect(db.DB_PATH) as old:
        old.executescript(db.SCHEMA)
        old.execute("INSERT INTO reminders (created_at, contact_book, heard_transcript, output_transcript,"
                    " entities_json, resolution) VALUES ('then','A','legacy','legacy','[]','auto')")
        old.execute("INSERT INTO pending (id, created_at, contact_book, heard_transcript, direction, phrase,"
                    " reason, candidates_json) VALUES ('0123456789abcdef','then','B','legacy','outgoing','x','x','[]')")
    assert api.get("/api/reminders").json() == []
    assert api.get("/api/reminders/1").status_code == 404
    assert api.delete("/api/reminders").json() == {"deleted": 0}
    assert api.post("/api/clarify/0123456789abcdef", json={"entity_id": "x", "remember": "this_time"}).status_code == 404
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM reminders WHERE visitor_id IS NULL").fetchone()[0] == 1
        assert conn.execute("SELECT status FROM pending WHERE visitor_id IS NULL").fetchone()[0] == "open"


def test_simultaneous_answers_create_one_reminder_and_one_preference(api, monkeypatch):
    from app.store import pending

    question = process(api, text=DOCTOR_SENTENCE, book="B").json()["pending"]["id"]
    both_ready = Barrier(2, timeout=5)
    claim = pending.claim

    def simultaneous_claim(*args):
        both_ready.wait()
        return claim(*args)

    monkeypatch.setattr(pending, "claim", simultaneous_claim)

    def submit(entity_id):
        return api.post(f"/api/clarify/{question}", json={"entity_id": entity_id, "remember": "always"})

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = sorted(pool.map(submit, ["person_001", "person_028"]), key=lambda r: r.status_code)
    assert [r.status_code for r in results] == [200, 409]
    assert "already answered" in results[1].json()["detail"]
    assert api.get("/api/reminders").json() == [results[0].json()["reminder"]]
    with loader.use_book("B"):
        assert [p.entity_id for p in loader.load_preferences()] == [results[0].json()["reminder"]["target_entity_id"]]
