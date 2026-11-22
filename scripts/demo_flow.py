"""
scripts/demo_flow.py — runs the "two contact books" doctor demo end to end through the API, step by step.

WHAT: The same sentence, "Remind me to call my doctor at six.", for two users:
        Book A (one doctor)                     -> reminder for Dr. Venkataramana, no question
        Book B (two doctors, no default)        -> Pehchaan ASKS
          answer "Use Dr. Subramanian this time" -> reminder, nothing learned; asking again still asks
          answer "Always use ... for 'my doctor'" -> reminder + a saved preference (consent)
          same sentence again                    -> resolved automatically (resolution = "preference")
      Before any learning, a clue in the sentence ("tooth") picks the dentist without asking.
      Finally the stored reminders are listed.
      With --compare, baseline (c) also answers the book-B sentence (one GPT-4o-mini call, ~$0.001).
WHY:  It is the demo script for the stage, and a living check that the whole flow works.

By default it runs IN-PROCESS (FastAPI TestClient) on a TEMPORARY database and temporary preference files,
so it never changes your demo state and needs no running server and no API key ($0).
With --url it drives a running server instead (uvicorn app.main:app), using that server's real data.

Run from the project root:
    python scripts/demo_flow.py
    python scripts/demo_flow.py --compare                    # + baseline (c) side by side (needs OPENAI key)
    python scripts/demo_flow.py --url http://127.0.0.1:8000  # against a running server (resets book B!)
"""

import argparse
import sys
import tempfile
from uuid import uuid4
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SENTENCE = "Remind me to call my doctor at six."


def show(step: str, body: dict) -> None:
    """Print one step the way a presenter would narrate it."""
    print(f"\n== {step}")
    if "heard_transcript" in body:
        print(f"   heard     : {body['heard_transcript']}")
    for s in body.get("spans", []):
        print(f"   entity    : '{s['heard_text']}' -> {s['resolved_name'] or 'kept as heard'}"
              f" ({s['confidence']:.2f})  why: {s['reason']}")
    if body.get("pending"):
        p = body["pending"]
        print(f"   ASKS      : which one is '{p['phrase']}'?")
        for c in p["candidates"]:
            print(f"               - {c['name']} ({c['role']})")
    if body.get("reminder"):
        r = body["reminder"]
        print(f"   REMINDER  : #{r['id']} {r['target_name']} ({r['target_role']}), time={r['time']}, "
              f"resolution={r['resolution']}")
    if body.get("saved_preference"):
        sp = body["saved_preference"]
        print(f"   LEARNED   : '{sp['phrase_pattern']}' -> {sp['entity_id']} (only because you chose 'always')")
    if body.get("baseline"):
        b = body["baseline"]
        print(f"   (c) says  : {b['behaviour']}, target={b['action']['target_entity_id']} "
              f"({body['timings']['baseline_ms']:.0f} ms, ${body['baseline_cost_usd']:.5f})")
    if "timings" in body:
        t = body["timings"]
        print(f"   cost/time : pehchaan {t['pehchaan_ms']:.1f} ms, LLM used: {body['used_llm']}, ${body['cost_usd']:.5f}")


def run(api, compare: bool) -> int:
    api.headers["X-Visitor-Id"] = str(uuid4())

    def post(url, **kw):
        r = api.post(url, **kw)
        if r.status_code != 200:
            print(f"[ERROR] {url}: {r.status_code} {r.text}")
            raise SystemExit(1)
        return r.json()

    def say(book, text=SENTENCE, cmp=False):
        return post("/api/process", data={"text": text, "book": book, "compare": str(cmp).lower()})

    def pick(pending, name, remember):
        eid = next(c["entity_id"] for c in pending["candidates"] if c["name"] == name)
        return post(f"/api/clarify/{pending['id']}", json={"entity_id": eid, "remember": remember})

    # 0. A clean slate for the demo.
    api.delete("/api/reminders")
    post("/api/preferences/reset", params={"book": "B"})
    for b in api.get("/api/books").json():
        print(f"Book {b['book']:<8} {b['description']}")

    show("1. Book A says it (one doctor)", say("A"))
    b1 = say("B", cmp=compare)
    show("2. Book B says the SAME sentence (two doctors, no default)", b1)
    show("3. Book B, with a clue in the sentence: 'tooth' -> the dentist, no question",
         say("B", "Call my doctor, my tooth is paining."))
    show("4. User answers step 2: 'Use Dr. Subramanian this time'", pick(b1["pending"], "Dr. Subramanian", "this_time"))
    b2 = say("B")
    show("5. Book B again: nothing was learned, so it asks again", b2)
    show("6. User taps \"Always use Dr. Subramanian for 'my doctor'\"", pick(b2["pending"], "Dr. Subramanian", "always"))
    show("7. Book B again: resolved automatically from what it learned", say("B"))
    reminders = api.get("/api/reminders").json()
    print(f"\n== 8. Stored reminders ({len(reminders)}), newest first")
    for r in reminders:
        print(f"   #{r['id']} book {r['contact_book']}: {r['target_name']:<18} {r['resolution']:<20} "
              f"heard: {r['heard_transcript']}")
    print("\n[OK] Demo flow finished.")
    return 0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Run the two-contact-books doctor demo through the API.")
    parser.add_argument("--url", default=None, help="drive a running server instead of an in-process app")
    parser.add_argument("--compare", action="store_true", help="also ask baseline (c) (one real LLM call)")
    args = parser.parse_args()

    if args.url:
        import httpx
        with httpx.Client(base_url=args.url, timeout=60) as api:
            return run(api, args.compare)

    # In-process: temporary database + temporary preference files, so real demo state is untouched.
    import app.kb.loader as loader
    import app.store.db as db
    from fastapi.testclient import TestClient

    from app.main import app
    with tempfile.TemporaryDirectory() as tmp:
        db.DB_PATH = Path(tmp) / "demo.db"
        loader.RUNTIME_PREFS_DIR = Path(tmp)
        print(f"(in-process run on a temporary database; your data/app.db is not touched)\n")
        return run(TestClient(app), args.compare)


if __name__ == "__main__":
    sys.exit(main())
