# AGENTS.md — run, test and evaluate Pehchaan

This file is for AI agents and reviewers who need to install Pehchaan on a fresh machine and use it end to end.
Every command and expected result below was checked on a fresh `git clone`, first with **no `.env`** and then with
an OpenAI key (see [Verified on a fresh clone](#verified-on-a-fresh-clone)).

## 1. What Pehchaan is

Pehchaan ("recognition") is a layer that runs **after speech-to-text** in a voice assistant. It fixes misheard Indian names,
places and businesses, and works out who "my doctor" or "Amma" means, using the user's own contacts. Then it creates
one real action, a stored **reminder**. It decides most cases with sound-alike + fuzzy matching (no LLM call needed),
uses GPT-4o-mini only when it is unsure, and **asks** when two contacts fit equally well. It always shows
*heard → resolved → confidence → reason*.

- **Live demo:** https://d1rcvr2z1hg6u0.cloudfront.net
- **Repository:** https://github.com/Sajidhussain19/pehchaan
- Built for Builders 2026 (OpenAI x Equal AI, Hyderabad), track "Voice AI for India".

## 2. Prerequisites

| Need | Details |
|---|---|
| Python | **3.12** (tested: 3.12.10 on Windows 11; the Docker image uses `python:3.12-slim` on Linux). 3.11 should also work, but it was not tested. |
| OS | Linux, macOS or Windows. All dependencies are pinned wheels (`requirements.txt`); no compiler, ffmpeg or database server is needed. SQLite comes with Python. |
| Disk / network | About 300 MB for the virtual environment, about 75 MB for the repo. Internet is needed for `pip install`, and for OpenAI only if you set a key. |
| Browser (for the UI) | Chrome or Edge. The **microphone only works on `http://localhost` or `https://`** (a browser rule). On a remote server opened by plain `http://<ip>`, everything except the mic works. |
| Optional | Docker (tested with Docker 29) as an alternative to the venv. An **OpenAI API key** for live speech-to-text, the live strong-AI comparison and the LLM fallback (see section 5). |

## 3. Environment variables

All settings are read by [app/config.py](app/config.py) from environment variables or from a `.env` file in the
repo root (names are case-insensitive). **Nothing is required to start the server, run the tests or use the demo
clips.** Template: [.env.example](.env.example).

| Variable | Required? | Default | What it does |
|---|---|---|---|
| `OPENAI_API_KEY` | Optional | none | Enables live speech-to-text (mic and audio upload), the live strong-AI comparison ("baseline (c)"), and Pehchaan's LLM fallback. Without it, these fail safely: the response says so, and nothing crashes. |
| `RATE_LIMIT_REQUESTS` | Optional | `20` | Maximum `POST /api/process` calls per client IP per window. **Automated testers should set this to `1000`**: the full journey list below makes more than 20 calls, and the 21st call within 10 minutes returns HTTP 429. |
| `RATE_LIMIT_WINDOW_SECONDS` | Optional | `600` | Length of that rate-limit window in seconds. Kept in memory, so a restart resets it. |
| `DAILY_BUDGET_USD` | Optional | `2.0` | Spend cap. Before each call that might use OpenAI, the server checks that today's (UTC) recorded spend plus $0.005 is still under this cap, otherwise it returns HTTP 503. Spend is stored in SQLite. Clip replays cost $0 and are never blocked. |
| `DEMO_KEY` | Optional | none | A shared password for a public demo. If set, every `POST`/`DELETE` under `/api/` needs the header `X-Demo-Key: <value>` (otherwise HTTP 401), and the web page asks for it once. |
| `ALLOWED_ORIGINS` | Optional | empty | Comma-separated extra origins (e.g. `https://dxxxx.cloudfront.net`) that browsers may call the API from. The app's own origin is always allowed. Requests without an `Origin` header (curl, scripts) are not affected. |
| `TRUST_PROXY` | Optional | `false` | Set to `true` only behind a reverse proxy/CDN (we use CloudFront). Then the client IP for the rate limit is read from `X-Forwarded-For`, and `X-Forwarded-Host/Proto` count as the app's own origin. |
| `STATE_DIR` | Optional | unset → `data/` and `data/kb/books/` | Folder for runtime state: `app.db` (reminders, pending questions, daily spend) and the learned preferences of books A/B (`preferences_<book>.json`). The Docker image sets `/app/state`. |
| `TRANSCRIPTION_MODEL` | Optional | `gpt-4o-mini-transcribe` | Speech-to-text model (`gpt-4o-transcribe` and `whisper-1` also work). |
| `CHAT_MODEL` | Optional | `gpt-4o-mini` | Model for Pehchaan's LLM fallback and for the strong-AI baseline. |
| `EMBEDDING_MODEL` | Optional | `text-embedding-3-small` | Not used by the app at runtime (kept for experiments). |
| `TTS_MODEL` / `TTS_FALLBACK_MODEL` | Optional | `gpt-4o-mini-tts` / `tts-1` | Only used by `scripts/build_audio.py`, which made the synthetic test audio. That audio is already in the repo. |
| `HF_TOKEN` | Optional | none | Only for `scripts/fetch_real_speech.py` (downloads the gated AI4Bharat Svarah real-speaker audio). |
| `PROJECT_NAME` | Optional | `Pehchaan` | Name shown by `/health` and the API docs. |

Learned preferences (the "Always use X" answers) are saved per contact book: `data/kb/books/preferences_<book>.json`
for books A/B (git-ignored, or in `STATE_DIR`), and `data/kb/preferences.json` for the full book. Reset one book with
`POST /api/preferences/reset?book=B`.

## 4. Install and start

### Option A: Python virtual environment (Linux / macOS)

```bash
git clone https://github.com/Sajidhussain19/pehchaan.git && cd pehchaan
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pytest -q                              # expect: 199 passed (about 45 s)
# optional: cp .env.example .env  and put your real OPENAI_API_KEY in it (delete the HF_TOKEN placeholder line)
export RATE_LIMIT_REQUESTS=1000        # recommended for automated testing (see section 3)
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

On **Windows PowerShell** the differences are: `python -m venv venv`, `.\venv\Scripts\Activate.ps1`,
`$env:RATE_LIMIT_REQUESTS = "1000"`, and in the examples below use `curl.exe` instead of `curl`.

Check it runs (in a second terminal):

```bash
curl -s http://127.0.0.1:8000/health
# {"status":"ok","project":"Pehchaan"}
```

Then open **http://127.0.0.1:8000** (the demo page) or **http://127.0.0.1:8000/docs** (interactive API docs).
Stop the server with `Ctrl+C`.

### Option B: Docker

```bash
docker build -t pehchaan .
# without a key (clips, typed sentences, doctor demo, scoreboard):
docker run --rm -p 8000:8000 -e RATE_LIMIT_REQUESTS=1000 -v pehchaan-state:/app/state pehchaan
# with a key: add  --env-file .env  (the key is never baked into the image; .dockerignore excludes .env)
curl -s http://127.0.0.1:8000/health
```

The image runs as a non-root user, has a `HEALTHCHECK` on `/health`, and keeps state in the `pehchaan-state` volume.
AWS deployment (EC2 + CloudFront, as used for the live demo): [DEPLOY.md](DEPLOY.md).

## 5. What works without an OpenAI key

Checked on a fresh clone with **no `.env` and no key in the environment**:

| Feature | Without key | Why |
|---|---|---|
| Server start, `/health`, `/docs`, the web page | ✅ works | |
| All tests (`pytest -q`) | ✅ 199 passed | OpenAI is faked in tests |
| **Demo clip replays** (s104, s140, s067, s090, s101, s185 and all other listed clips, Clean or Phone) | ✅ works, $0 | They replay the **saved** speech-to-text transcript and the **saved** Pehchaan and strong-AI decisions from the evaluation run, with ✓/✗ verdicts |
| Clip audio playback (`/audio/...wav`) | ✅ works | WAV files are in the repo |
| **Typed sentences** | ✅ works whenever the fast path decides (most sentences, e.g. the tooth → dentist example) | No speech-to-text and no LLM is needed |
| **5-step doctor demo** (books A and B, clarify, "Always use", learned preference, clue wins) | ✅ works fully | Everything is on the fast path. The Strong AI card shows "Strong AI unavailable (RuntimeError) — comparison skipped" |
| Reminders list, reminder detail, Reset demo | ✅ works | SQLite |
| Scoreboard (`/api/metrics`) | ✅ works | Reads committed reports |
| Dev evaluation (`scripts/evaluate.py`) and `scripts/demo_flow.py` | ✅ works, $0 | Score saved outputs |
| **Live mic / audio upload** | ❌ needs key | HTTP 503: "Speech-to-text is unavailable right now (RuntimeError). Demo clips and typed sentences still work." |
| **Live strong-AI comparison** on typed sentences, mic, books A/B or with `live_baseline=true` | ❌ needs key | `baseline_error: "Strong AI unavailable (RuntimeError) — comparison skipped"`; Pehchaan's own answer is still returned |
| **Pehchaan's LLM fallback** (only for unsure spans, ~7–13% of clips) | ❌ needs key | Fails safe: it **asks** instead of guessing; reason `clarify: AI unavailable — asked you instead`, and `ai_unavailable: true` |

With a key, a typed sentence with comparison on costs about $0.001–0.002 (strong AI only; Pehchaan's fast path is $0),
and a mic recording costs about $0.0002 for speech-to-text, plus the strong AI if comparison is on.

## 6. Test logins

**There is no login and there are no user accounts.** Each browser makes a random UUIDv4 "visitor id" on first visit
(stored in `localStorage`) and sends it as the `X-Visitor-Id` header. Reminders and pending questions belong to that
visitor id. API callers must send their own UUIDv4 (any `uuid4()`); without it, `/api/process`, `/api/clarify` and
`/api/reminders` return HTTP 400 `X-Visitor-Id must be a valid random UUID (v4)`.
Learned preferences are shared per **contact book**, not per visitor.

If the operator sets `DEMO_KEY`, the page shows a "Demo key" dialog once. API callers add `-H "X-Demo-Key: <value>"`
to every POST/DELETE. The local default is **no demo key**.

All contacts in the knowledge base are **fictional**.

## 7. End-to-end journeys in the browser

Open http://127.0.0.1:8000. Defaults: contact book **Full contacts (evaluated)**, **Compare with strong AI** on,
audio **Clean**. The left column has **Demo clips** (each with **▶ Play** and **Run**), **Try it yourself**
(mic) and **Or type a sentence**. The middle shows two cards, **Strong AI (GPT-4o-mini with the same contacts)**
and **Pehchaan**. The right column shows **Reminders**. Clip runs are *previews* ("Would create a reminder…"):
they never store a reminder. Typed, mic and doctor-demo runs store real reminders.

| # | Click | Expected result |
|---|---|---|
| 1 | Clip **s104 · missed clarification — Rohit vs Rohith** → **Run** | Said "Call Rohit at 6 PM." Strong AI: **✗ Wrong target** (would remind Rohith Reddy). Pehchaan: **✓ Correct**, asks "Rohit Chaturvedi or Rohith Reddy?", "Matched without an AI call". |
| 2 | Clip **s140 · clue vs default — tooth → dentist** → **Run** | Strong AI: **✗ Wrong target** (family doctor Dr. Venkataramana). Pehchaan: **✓ Correct**, "my doctor" → **Dr. Subramanian (dentist)**, 90%, reason "clue 'tooth' -> dentist; clue 'filling' -> dentist". Click the highlighted "my doctor" for the *why*. |
| 3 | Clip **s067 · misheard name — Bhagyalakshmi Jewellers, Panjagutta** → **Run** | Heard "Call **Padyalakshmi Jewelers** in **Punjabuta**…". Strong AI: **✗ Wrong decision** (changes nothing). Pehchaan: **✓ Correct**, → **Bhagyalakshmi Jewellers** (87%) and **Panjagutta** (88%), no LLM. |
| 4 | Clip **s090 · v1 failure — fixed in v2** → **Run** | Telugu "ఈ రోజు…" ("ee roju" = *today*). Shows v1's old output "ii **Dr. Raju** chaalaa…"; v2 **keeps** it ("everyday speech, not a name"). Both cards **✓ Correct**. |
| 5 | Switch audio to **Phone**, clip **s101 · near-identical names — Harshit or Harshil?** → **Run** | Heard "Call Harshit at five." Strong AI: **✗ Wrong target** (Harshit Sharma). Pehchaan: **✓ Correct**, asks between Harshit Sharma, Harshil Patel and Harjeet Kaur. (On Clean audio both are ✓.) Switch back to **Clean** afterwards. |
| 6 | Scroll the clip list to group **Held-out test-2 (v2)**, clip **s185 · Known failure (v2)** → **Run** | **Honest failure.** Heard "Tell Dhiraj to bring the projector to the Shadnagar office." Pehchaan: **✗ Wrong target**, "Dhiraj" → **Dr. Raju (eye specialist)**, 84%. Strong AI: **✓ Correct**. |
| 7 | Click **▶ Start the 5-step doctor demo** (header), then **Next ▶** after each step | Step 1 (book A): "Remind me to call my doctor at 6 PM." → reminder **Dr. Venkataramana (family doctor) 18:00**. Step 2 (book B): Pehchaan **asks** "who is 'my doctor'?" (Dr. Venkataramana, general physician / Dr. Subramanian, dentist). Step 3: clicks **Always use for 'my doctor'** on Dr. Subramanian → reminder **Dr. Subramanian 18:00**, "Learned for book B". Step 4: the same sentence → **Dr. Subramanian** automatically (from the learned preference). Step 5: "Call my doctor about my fever." → **Dr. Venkataramana (general physician)**: the clue beats the saved preference. Click **Finish**. Without a key, the Strong AI card says the comparison was skipped. |
| 8 | Type **Remind me to call my doctor about my tooth at 6 PM.** in *Or type a sentence* → **Run** (book: Full contacts) | Pehchaan: "my doctor" → **Dr. Subramanian (dentist)**, clue 'tooth', **reminder at 18:00** appears on the right, no LLM call. With a key the Strong AI card also answers (in our run it picked the family doctor). |
| 9 | Mic: **Tap to record**, say "Remind me to call my doctor about my tooth at 6 PM.", tap again (max 15 s). Needs key + localhost/https. | Live transcript, then the same dentist reminder at 18:00. Shows real speech-to-text time (~1.5 s) and cost (~$0.0002). Without a key: banner "Speech-to-text is unavailable right now…". |
| 10 | Click any reminder in **Reminders** | A dialog with person, role, time, contact book, created time, heard vs corrected transcript, and "Name resolutions" (`'my doctor' → Dr. Subramanian (dentist) · automatic match`). |
| 11 | Tab **Scoreboard** | Top: **Fresh held-out test (v2, test-2)**: wrong targets **Strong AI 10/90 → Pehchaan v2 2/90**; **25 wins / 62 ties / 3 losses**; "Still worse: 4 unnecessary questions vs 0". Below: **Original held-out test (v1)**: wrong targets 24/220 vs 11/220; 49 / 149 / 22. |
| 12 | Tab **Live demo** → **Reset demo** (top of Reminders) → confirm | Banner "Demo reset: reminders cleared, book … forgot its learned answers." The reminder list empties. |

## 8. The same journeys via the API (curl)

```bash
B=http://127.0.0.1:8000
V=$(python -c "import uuid; print(uuid.uuid4())")      # your visitor id (any UUIDv4)

curl -s $B/health
curl -s $B/api/books                                    # default, A, B
curl -s $B/api/clips | head -c 600                      # 76 clips; featured ones first
curl -s -o s104.wav $B/audio/clean/s104.wav             # clip audio

# Clip replays ($0, no key): read decision.behaviour, names, verdict.pehchaan / verdict.baseline
curl -s -X POST $B/api/process -H "X-Visitor-Id: $V" -F clip_id=s104 -F variant=clean -F compare=true
curl -s -X POST $B/api/process -H "X-Visitor-Id: $V" -F clip_id=s140 -F variant=clean -F compare=true
curl -s -X POST $B/api/process -H "X-Visitor-Id: $V" -F clip_id=s067 -F variant=clean -F compare=true
curl -s -X POST $B/api/process -H "X-Visitor-Id: $V" -F clip_id=s090 -F variant=clean -F compare=true
curl -s -X POST $B/api/process -H "X-Visitor-Id: $V" -F clip_id=s101 -F variant=phone -F compare=true
curl -s -X POST $B/api/process -H "X-Visitor-Id: $V" -F clip_id=s185 -F variant=clean -F compare=true

# Typed sentence -> stored reminder: reminder.target_name "Dr. Subramanian", reminder.time "18:00"
curl -s -X POST $B/api/process -H "X-Visitor-Id: $V" \
  -F "text=Remind me to call my doctor about my tooth at 6 PM." -F compare=false

# Doctor demo
curl -s -X POST "$B/api/preferences/reset?book=B"
curl -s -X POST $B/api/process -H "X-Visitor-Id: $V" -F "text=Remind me to call my doctor at 6 PM." -F book=A -F compare=false
#   -> reminder Dr. Venkataramana 18:00
curl -s -X POST $B/api/process -H "X-Visitor-Id: $V" -F "text=Remind me to call my doctor at 6 PM." -F book=B -F compare=false
#   -> decision.behaviour "clarify", reminder null, pending.id "<16 hex>", pending.candidates person_001 / person_028
curl -s -X POST $B/api/clarify/<pending.id> -H "X-Visitor-Id: $V" -H "Content-Type: application/json" \
  -d '{"entity_id":"person_028","remember":"always"}'
#   -> reminder Dr. Subramanian 18:00, resolution "clarified_always"  ("this_time" would learn nothing)
curl -s -X POST $B/api/process -H "X-Visitor-Id: $V" -F "text=Remind me to call my doctor at 6 PM." -F book=B -F compare=false
#   -> Dr. Subramanian, resolution "preference"
curl -s -X POST $B/api/process -H "X-Visitor-Id: $V" -F "text=Call my doctor about my fever." -F book=B -F compare=false
#   -> Dr. Venkataramana (general physician), reason "resolve: clue 'fever' -> general physician; beats your saved choice"

# Mic equivalent: upload audio (needs key; webm/ogg/wav/mp3/m4a, <= 5 MB, <= 30 s)
curl -s -X POST $B/api/process -H "X-Visitor-Id: $V" -F "file=@data/testset/audio/clean/s104.wav" -F compare=false
#   -> stt_source "live gpt-4o-mini-transcribe", heard "Call Rohit at 6 p.m.", behaviour "clarify"

# Reminders, detail, scoreboard, reset
curl -s $B/api/reminders -H "X-Visitor-Id: $V"
curl -s $B/api/reminders/<id> -H "X-Visitor-Id: $V"
curl -s $B/api/metrics                                   # win_tie_loss {win:49, tie:149, loss:22}; v2 block for test-2
curl -s -X DELETE $B/api/reminders -H "X-Visitor-Id: $V" # Reset demo = this + preferences/reset
```

Other `POST /api/process` fields: `live_stt=true` re-transcribes a clip live (key), `live_baseline=true` runs the
strong AI live on a clip instead of replaying it (key), and `direction` / `caller_contact_id` set the call context.
The response always includes `heard_transcript`, `output_transcript`, `decision.entities[]`
(heard_text, resolved_entity_id, confidence, reason), `used_llm`, `timings` and `cost_usd`. Full schema: `/docs`.

## 9. Tests and evaluation reports

```bash
pytest -q                                   # 199 passed; no key or network needed
python scripts/evaluate.py --out dev_check  # re-scores the DEV split from saved outputs, $0, no key
#   -> data/results/dev_check.md (+ .json). It matches the committed data/results/report_dev_all.md:
#      Pehchaan v2 wins 54, ties 88, loses 4 vs the strong AI; wrong targets 0/146 vs 20/146.
#      (The console line "c vs pehchaan: {'loss': 54, 'win': 4, ...}" counts from (c)'s side.)
python scripts/demo_flow.py                 # the two-book doctor story through the API, $0, temporary DB
```

**Held-out runs are already done and must not be repeated.** `--split test` needs `--final`, and `--split test2`
needs `--final-test2`. Both are logged in `data/results/test_runs.log`. The frozen reports are
`data/results/report_test_FINAL.md` (tags `final-eval-v1`, `final-eval-v1.1`) and `data/results/report_test2_FINAL.md`
(tags `test2-frozen` → `pehchaan-v2`). `tests/test_freeze.py` checks that the decision logic still matches the
fingerprint of the evaluated version.

Re-running the systems themselves (`scripts/run_baseline.py`, `run_llm_baseline.py`, `run_pehchaan.py`) needs a key.
They default to the dev split and skip clips that are already saved.

## 10. Repo map

| Path | What it is |
|---|---|
| `app/main.py` | FastAPI app: `/health`, API router, security middleware, serves `web/` |
| `app/config.py` | All settings (section 3) |
| `app/api/` | HTTP endpoints (`routes.py`), request flow (`flow.py`), audio checks, demo guards (`guard.py`) |
| `app/match/` | Span detection + phonetic/fuzzy matching with confidence (frozen) |
| `app/decide/` | LangGraph decision pipeline: resolve / LLM check / clarify / keep; v2 rules (frozen) |
| `app/kb/` | Loads the knowledge base and the demo contact books |
| `app/store/` | SQLite reminders, pending questions, learned preferences |
| `app/stt/` | OpenAI speech-to-text (live + baselines a/b) |
| `app/baselines/` | Strong LLM baseline (c) |
| `app/eval/` | Metrics, scoring and reports |
| `app/testset/` | Test-set schema and validation |
| `web/` | Demo page (plain HTML/CSS/JS, no build step) |
| `data/kb/` | Fictional contacts, Indian places, businesses; `books/` = demo books A and B |
| `data/lexicon/` | Everyday Indian-language words (v2 over-correction guard) |
| `data/testset/` | Test sentences + synthetic TTS audio (clean + phone quality) |
| `data/realspeech/` | Manifest + attribution for real Svarah speakers (audio not included) |
| `data/results/` | Saved transcripts, decisions and all evaluation reports |
| `scripts/` | Command-line tools (evaluate, run baselines, demo flow, fetch real speech, freeze check) |
| `tests/` | pytest suite (199 tests) |
| `deliverables/` | Slide deck (PDF + PPTX), cheat sheet, demo video (see [VIDEO.md](VIDEO.md)) |
| `Dockerfile`, `deploy/`, `DEPLOY.md` | Container and AWS deployment |
| `README.md`, `LEARNING.md`, `DEMO_SCRIPT.md`, `CLAUDE.md` | Overview and results, module-by-module notes, demo script, project brief |

## 11. Results summary

Strong AI (c) = one GPT-4o-mini call that gets the same transcript and the user's whole personal context, and is
allowed to ask.

- **Fresh held-out test-2** (90 clips, frozen before v2 existed, run once): wrong actions **10 → 2**
  (strong AI 10/90, Pehchaan v2 2/90). Clip by clip: **25 wins, 62 ties, 3 losses**.
  **Still worse: 4 unnecessary questions** (4/78) vs 0 for the strong AI.
- **Original held-out test** (220 clips incl. 26 real speakers, run once, v1): wrong actions **24 → 11**;
  missed clarifications 14/14 → 1/14; reference resolution 19/32 → 32/32; 87% decided without any LLM call;
  median decision latency 11 ms vs 1502 ms. Weak spots: over-correction 11/70 vs 3/70, unnecessary questions 15/198 vs 0.
- Details with raw counts: [README.md](README.md#results-held-out-test-split-run-once) and `data/results/`.

## 12. Known limits

- **s185:** an unknown name that sounds like a contact ("Dhiraj" → "Dr. Raju") can still be corrected wrongly.
- Asks more often than the strong AI (4 unnecessary questions on test-2).
- One action only (**Remind**). Call/Book are scored as targets but not executed.
- Times are parsed simply ("6 PM" → 18:00); a vague time is stored as none.
- The knowledge base is one user's personal context (340 fictional entries), not every name in India.
- Live mic needs an OpenAI key and `localhost`/`https`. Public demo limits: 20 requests per 10 minutes per IP and about $2/day.

## 13. Honest notes

- Built **solo** during a 28-hour hackathon **with AI coding agents**, in 10 modules (notes per module in [LEARNING.md](LEARNING.md)).
- All contacts are **fictional**. Places are public Indian locality names.
- Test audio is **synthetic** (OpenAI TTS, clean + simulated phone quality), plus **26 real Indian-accented speakers**
  from AI4Bharat **Svarah** (CC BY 4.0). The Svarah audio is **not redistributed** in this repo; its manifest,
  attribution, transcripts and results are. To fetch it: `HF_TOKEN=... python scripts/fetch_real_speech.py` (needs a Hugging Face token and
  accepting the dataset terms). Everything above works without it.
- The decision logic was frozen before the held-out runs, and no tuning was done on held-out results.
  The one approved change and the v2 unfreeze are disclosed in [README.md](README.md#decision-logic-freeze).

## Verified on a fresh clone

On 2026-11-22, a `git clone` of this repo into an empty folder on Windows 11, Python 3.12.10, following this file literally:

- **No `.env`, no key:** `pip install -r requirements.txt` OK → `pytest -q`: **199 passed** → server started →
  `/health` OK → every curl in section 8 gave the results shown (clip replays with the verdicts in section 7, doctor
  demo through book A/B + clarify + preference + clue, typed sentence → Dr. Subramanian 18:00, scoreboard
  49/149/22 and 25/62/3) → audio upload returned the expected 503 → `scripts/evaluate.py --out dev_check`
  reproduced `report_dev_all.md` → `scripts/demo_flow.py` finished. Without `RATE_LIMIT_REQUESTS`, the 21st process
  call returned 429, as designed.
- **Docker (Option B), no key:** `docker build` OK; the container reported `healthy`, and the same section-8 curls gave identical results.
- **With a `.env` containing a key:** typed sentence → Dr. Subramanian 18:00, plus a live strong-AI answer
  (it picked the family doctor; 2.8–3.3 s, $0.001–0.002); audio upload → live transcript "Call Rohit at 6 p.m." in
  ~1.5 s ($0.00017) → clarify; the LLM fallback and the live baseline also ran.
