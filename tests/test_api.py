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

import io
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


@pytest.fixture
def fake():
    return FakeOpenAI()


@pytest.fixture
def api(tmp_path, monkeypatch, fake):
    """A TestClient with a temporary database, temporary preference files and the fake OpenAI client."""
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "app.db")
    monkeypatch.setattr(loader, "RUNTIME_PREFS_DIR", tmp_path)
    monkeypatch.setattr(loader, "PREFERENCES_PATH", tmp_path / "preferences_default.json")
    app.dependency_overrides[openai_client] = lambda: fake
    yield TestClient(app)
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
    assert body["stt_source"].startswith("saved") and body["reminder"]["target_name"] == "Dr. Subramanian"
    assert not fake.calls
    assert api.get("/audio/phone/s140.wav").headers["content-type"] == "audio/wav"


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
    assert "held-out" in m["label"] and set(m["overall"]) == {"c", "pehchaan"}
    assert m["overall"]["pehchaan"]["wrong_target_rate"]["total"] > 0  # raw counts, not just a percentage
    clips = api.get("/api/clips").json()
    assert clips[0]["group"].startswith("demo") and any(c["group"] == "dev" for c in clips)
    process(api, text=DOCTOR_SENTENCE, book="A")
    assert api.delete("/api/reminders").json() == {"deleted": 1} and api.get("/api/reminders").json() == []
