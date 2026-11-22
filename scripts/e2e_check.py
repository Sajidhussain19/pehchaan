"""Verify the judge journeys against the HTTP API. Run from the project directory."""
import argparse
import os
import socket
import sys
import tempfile
import threading
import time
from contextlib import contextmanager, nullcontext
from pathlib import Path
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parents[1]
DOCTOR = "Remind me to call my doctor at 6 PM."
TOOTH = "Remind me to call my doctor about my tooth at 6 PM."
DENTIST = "Dr. Subramanian"
PHYSICIAN = "Dr. Venkataramana"
# Expected public outcomes in AGENTS.md, in Pehchaan / Strong AI order.
REPLAYS = (
    ("s104", "clean", "ok", "wrong_target"),
    ("s140", "clean", "ok", "wrong_target"),
    ("s067", "clean", "ok", "wrong_behaviour"),
    ("s090", "clean", "ok", "ok"),
    ("s101", "phone", "ok", "wrong_target"),
    ("s185", "clean", "wrong_target", "ok"),
)


def expect(actual, expected, label):
    if actual != expected:
        raise ValueError(f"{label}: expected {expected!r}, got {actual!r}")


def verify(api):
    """Accept an httpx.Client or TestClient. Return a process exit code."""
    api.headers["X-Visitor-Id"] = str(uuid4())
    rows = []

    def check(label, fn, *args):
        try:
            detail = fn(*args)
        except (httpx.HTTPError, ValueError, TypeError, KeyError, IndexError, RuntimeError) as exc:
            rows.append(("FAIL", label, str(exc)))
        else:
            rows.append(("PASS", label, detail or ""))

    def request(method, path, **kwargs):
        response = api.request(method, path, **kwargs)
        response.raise_for_status()
        return response.json()

    def say(text, book="default", compare=False):
        return request("POST", "/api/process", data={"text": text, "book": book, "compare": str(compare).lower()})

    def reminder(body, name, at, resolution):
        r = body["reminder"]
        if r is None:
            raise ValueError(f"expected a stored reminder for {name}, got no reminder")
        expect((r["target_name"], r["time"], r["resolution"]), (name, at, resolution), "saved reminder")
        return r

    def catalogue():
        books = request("GET", "/api/books")
        expect(sorted(b["book"] for b in books), ["A", "B", "default"], "books")
        ids = {c["clip_id"] for c in request("GET", "/api/clips")}
        expect([cid for cid, *_ in REPLAYS if cid not in ids], [], "missing featured clips")
        return f"{len(ids)} clips; books A, B and default"

    def audio():
        r = api.get("/audio/clean/s104.wav")
        r.raise_for_status()
        expect((r.content[:4], r.content[8:12]), (b"RIFF", b"WAVE"), "WAV signature")
        return r.content

    def replay(cid, variant, peh, strong):
        body = request("POST", "/api/process", data={"clip_id": cid, "variant": variant, "compare": "true"})
        outcomes = body["verdict"]
        expect((outcomes["pehchaan"]["outcome"], outcomes["baseline"]["outcome"]), (peh, strong), "verdicts")
        expect((body["decision_source"], body["baseline_source"]),
               ("saved evaluation replay", "saved evaluation replay"), "sources")
        expect((body["reminder"], body["pending"]), (None, None), "preview")
        return f"Pehchaan {peh} / Strong AI {strong}"

    def typed():
        expect(request("GET", "/api/reminders"), [], "reminders after replays")
        r = reminder(say(TOOTH), DENTIST, "18:00", "auto")
        return f"{r['target_name']} at {r['time']}"

    def doctor_demo():
        request("POST", "/api/preferences/reset", params={"book": "B"})
        reminder(say(DOCTOR, "A"), PHYSICIAN, "18:00", "auto")
        b = say(DOCTOR, "B")
        expect((b["decision"]["behaviour"], b["reminder"]), ("clarify", None), "book B asks")
        pending = b["pending"]
        choices = {c["name"]: c["entity_id"] for c in pending["candidates"]}
        expect(set(choices), {DENTIST, PHYSICIAN}, "offered doctors")
        answer = request("POST", f"/api/clarify/{pending['id']}",
                         json={"entity_id": choices[DENTIST], "remember": "always"})
        reminder(answer, DENTIST, "18:00", "clarified_always")
        expect(answer["saved_preference"]["entity_id"], choices[DENTIST], "learned doctor")
        reminder(say(DOCTOR, "B"), DENTIST, "18:00", "preference")
        fever = say("Call my doctor about my fever.", "B")
        reminder(fever, PHYSICIAN, None, "auto")
        expect(any("fever" in s["reason"].lower() for s in fever["spans"]), True, "fever clue")
        return "A default / B asks / always / learned / fever overrides"

    def detail():
        listed = request("GET", "/api/reminders")
        expect(len(listed), 5, "stored reminders")
        learned = next((r for r in listed if r["resolution"] == "preference"), None)
        if learned is None:
            raise ValueError("learned reminder missing from list")
        item = request("GET", f"/api/reminders/{learned['id']}")
        expect((item["heard_transcript"], item["target_name"], item["time"]), (DOCTOR, DENTIST, "18:00"), "detail")
        expect(any(e["name"] == DENTIST and e["method"] == "learned preference" for e in item["entities"]),
               True, "named resolution")
        return "5 stored; learned dentist reminder opens"

    def metrics():
        m = request("GET", "/api/metrics")
        for result, counts in ((m["v2"], (25, 62, 3)), (m, (49, 149, 22))):
            expect(tuple(result["win_tie_loss"][k] for k in ("win", "tie", "loss")), counts, "wins/ties/losses")
        for system, hits in (("c", 10), ("v2", 2)):
            rate = m["v2"]["overall"][system]["wrong_target_rate"]
            expect((rate["hits"], rate["total"]), (hits, 90), "wrong targets")
        return "test-2 25/62/3 (10 -> 2 wrong); original 49/149/22"

    def speech(configured):
        r = api.post("/api/process", files={"file": ("s104.wav", audio(), "audio/wav")}, data={"compare": "false"})
        if configured:
            r.raise_for_status()
            body = r.json()
            expect(body["stt_source"].startswith("live "), True, "live STT")
            expect(bool(body["heard_transcript"].strip()), True, "transcript")
            expect(body["decision"]["behaviour"], "clarify", "Rohit ambiguity")
            return "live transcript; asks which Rohit"
        else:
            expect(r.status_code, 503, "keyless upload")
            expect("Speech-to-text is unavailable" in r.json()["detail"], True, "keyless explanation")
            return "HTTP 503 explains how to continue"

    def comparison(configured):
        b = say(TOOTH, compare=True)
        reminder(b, DENTIST, "18:00", "auto")
        if configured:
            expect((b["baseline_source"], bool(b["baseline"])), ("live", True), "live comparison")
            return "both live decisions returned"
        else:
            expect(b["baseline"], None, "keyless Strong AI")
            expect("comparison skipped" in (b["baseline_error"] or ""), True, "keyless explanation")
            return "dentist reminder saved; comparison skipped"

    def reset():
        request("DELETE", "/api/reminders")
        reset_book = request("POST", "/api/preferences/reset", params={"book": "B"})
        expect(reset_book["removed"], 1, "learned preferences cleared")
        expect(request("GET", "/api/reminders"), [], "empty reminder list")
        return "empty list; learned preference cleared"

    check("Health", lambda: expect(request("GET", "/health")["status"], "ok", "health"))
    check("Books and clips", catalogue)
    check("Clip audio", lambda: f"{len(audio())} bytes of WAV")
    for cid, variant, peh, strong in REPLAYS:
        check(f"{cid} {variant}", replay, cid, variant, peh, strong)
    check("Typed tooth request", typed)
    check("Five-step doctor demo", doctor_demo)
    check("Reminders list and detail", detail)
    check("Scoreboard", metrics)

    try:
        configured = request("GET", "/api/config")["live_ai_configured"]
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        rows.append(("FAIL", "Live AI configuration", str(exc)))
    else:
        if configured:
            check("Live transcription", speech, True)
            check("Live Strong AI comparison", comparison, True)
        else:
            check("Keyless speech error", speech, False)
            check("Keyless comparison", comparison, False)
            for label in ("Live transcription", "Live Strong AI comparison"):
                rows.append(("SKIPPED", label, "server has no OpenAI key"))
    check("Reset reminders and book B", reset)

    print(f"{'STATUS':<8} {'JOURNEY':<27} RESULT")
    for status, label, detail in rows:
        print(f"{status:<8} {label:<27} {detail}")
    counts = [sum(row[0] == status for row in rows) for status in ("PASS", "FAIL", "SKIPPED")]
    print(f"{'FAILED' if counts[1] else 'ALL PASSED'} ({counts[0]} passed, {counts[1]} failed, {counts[2]} skipped)")
    return int(counts[1] > 0)


@contextmanager
def local_server():
    """Bind a private ephemeral port and isolate both SQLite and book preferences."""
    import uvicorn

    sys.path.insert(0, str(ROOT))
    with tempfile.TemporaryDirectory() as state, socket.socket() as sock:
        os.environ.update(STATE_DIR=state, RATE_LIMIT_REQUESTS="1000")
        sock.bind(("127.0.0.1", 0))
        config = uvicorn.Config("app.main:app", log_level="error", access_log=False)
        server = uvicorn.Server(config)
        thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 30
            while not server.started:
                if not thread.is_alive() or time.monotonic() >= deadline:
                    raise RuntimeError("local server did not start within 30 seconds")
                time.sleep(.05)
            yield f"http://127.0.0.1:{sock.getsockname()[1]}"
        finally:
            server.should_exit = True
            thread.join()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", help="Use a running test server. This resets its shared book B preference.")
    args = parser.parse_args()
    target = nullcontext(args.base_url) if args.base_url else local_server()
    try:
        with target as url, httpx.Client(base_url=url, timeout=45, trust_env=False) as api:
            if key := os.environ.get("DEMO_KEY"):
                api.headers["X-Demo-Key"] = key
            return verify(api)
    except (OSError, ValueError, RuntimeError, httpx.HTTPError) as exc:
        print(f"FAIL  Server: {exc}\nFAILED")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
