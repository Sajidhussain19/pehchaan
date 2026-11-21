# Pehchaan — Learning Notes

One section per module: what we built, how it works, key concepts, and questions a judge might ask.

---

## Module 1 — Project setup

### What we built
The base of the project, with no "AI" yet:
- A **FastAPI** web app with one endpoint, `GET /health`, that returns `{"status": "ok", "project": "Pehchaan"}`.
- A **settings file** (`app/config.py`) that reads the OpenAI key and model names from a `.env` file.
- A **check script** (`scripts/check_openai.py`) that makes one tiny OpenAI call to prove the key works.
- A **test** (`tests/test_health.py`) that checks `/health` automatically.
- The folder structure for every later module, plus `README.md`, `CLAUDE.md`, `.gitignore`, `.env.example`.

### How it works
1. When the app starts, `app/config.py` creates one `Settings` object. pydantic-settings fills each field
   from environment variables or `.env`, and uses the default when a value is missing.
2. `app/main.py` creates the FastAPI `app` and registers `/health`.
3. **Uvicorn** is the server. It listens on a port (8000), receives HTTP requests and hands them to FastAPI.
4. FastAPI calls our `health()` function and turns the returned dict into JSON.
5. In tests, **TestClient** calls the app in memory, without a real server, and we check the reply with `assert`.

### Key concepts
- **Virtual environment (venv):** a private folder of Python packages just for this project. Each project gets
  its own versions, so projects don't conflict, and AWS can reproduce the exact setup.
- **requirements.txt + pinning:** the list of packages with exact versions (`fastapi==0.115.6`).
  Pinning means "install this exact version", so the code behaves the same on every machine.
- **FastAPI:** a Python web framework. You write normal functions, mark them with `@app.get("/path")`,
  and FastAPI turns them into HTTP endpoints. It also builds interactive docs at `/docs` for free.
- **Uvicorn:** an ASGI server, the program that actually runs the web app and talks to the network.
  (ASGI is the standard interface between Python web apps and servers.)
- **Endpoint:** a URL plus an HTTP method (GET, POST...) that the app answers. `GET /health` is one.
- **Health check:** a cheap endpoint that answers "I'm alive". Deploy tools and load balancers call it to
  decide whether the app is running.
- **Environment variables / `.env`:** settings that live outside the code. Secrets like API keys go here,
  never in source code. `.env` is git-ignored. `.env.example` shows the variable *names* only.
- **pydantic-settings:** reads env variables into a typed Python class. It checks types and fills defaults.
- **SecretStr:** a pydantic type that prints as `**********`, so a key can't leak into logs by accident.
- **pytest / TestClient:** pytest finds functions named `test_*` and runs them. A failing `assert` means a failed test.
  TestClient sends fake HTTP requests straight to the app.
- **.gitignore:** tells git which files never to track (secrets, venv, caches).
- **Exit code:** a number a program returns when it ends. 0 means success, anything else means failure.
  `check_openai.py` returns 1 on errors, so scripts and CI can detect the failure.

### A real bug we hit (and fixed)
The first version of `check_openai.py` printed emoji (✅ ❌). Some Windows terminals use an old text encoding
(cp1252) that has no emoji, so Python crashed with `UnicodeEncodeError`. We switched to plain `[OK]` /
`[ERROR]` markers, which work in every terminal. Lesson: test on the platform you'll actually demo on.

We also pinned `anyio==4.8.0`. A newer anyio caused a deprecation warning inside FastAPI's test client.

### Questions a judge might ask about this module
- **Why FastAPI and not Flask?** FastAPI has built-in data validation with Pydantic, automatic API docs at `/docs`,
  and async support. Those suit an API that calls OpenAI. It is also simple to explain.
- **How do you keep your API key safe?** It lives only in `.env`, which is in `.gitignore`. The code reads it
  through pydantic-settings as a `SecretStr`, so it is never hard-coded, committed or printed.
- **Why have a /health endpoint at all?** It is the simplest proof the server is up. On AWS it lets us
  (and any load balancer) check the app is alive without calling OpenAI.
- **Why pin versions?** So the demo machine and the EC2 server install exactly what we tested. No surprise upgrades.
- **Why put model names in config?** So we can swap models (e.g. a newer transcription model) with a one-line `.env`
  change and compare them, without touching code.
- **Why write tests in a 28-hour hackathon?** Each module builds on the last. A quick test catches a broken
  import or config immediately, which is cheaper than finding it during the demo.

---

## Module 2 — Knowledge base

### What we built
- `data/kb/contacts.json` (121 fictional contacts), `places.json` (145 places), `businesses.json` (61 fictional businesses): **327 entities, 481 aliases**.
- `app/kb/models.py`: Pydantic models. An `Entity` has id, name, type, aliases, language_origin, difficulty and context.
  Each type also has a context model: `PersonContext`, `PlaceContext`, `BusinessContext`.
- `app/kb/loader.py`: `load_kb()`, `get_by_type()`, `get_by_id()`, `all_surface_forms()`, plus whole-KB validation and caching.
- `scripts/kb_stats.py`: a friendly summary of the KB.
- `tests/test_kb.py`: 14 tests, covering both good data and deliberately broken data.

### How it works
1. `load_kb()` reads the three JSON files and turns each row into an `Entity`. Pydantic checks every field.
   It rejects a wrong type, a missing field, a real-looking phone number, or a typo in a context key.
2. `validate_entities()` then checks rules that need the whole KB at once:
   - ids are unique
   - no empty names
   - no two entities share a canonical name
   - no alias equals another entity's canonical name
   - every business `area` exists in `places.json`
   It collects *all* problems and reports them together.
3. The result is cached with `lru_cache`, so the disk is read once, however often the KB is asked for.
4. `all_surface_forms()` builds the lookup later modules will match against. It maps every name and alias
   (lower-cased) to entity ids: `{"kukatpalli": ["place_002"], ...}`.

### Why a knowledge base is needed
A speech-to-text model has never heard of *your* doctor, Dr. Venkataramana, or the pharmacy at the end of your street.
It guesses from common English sounds, so "Kukatpally" becomes "cook at Polly". No model can know your personal contacts.
The KB is the "personal context" in Equal AI's *context -> intent -> action*. It is the list of correct answers we
correct towards. The KB's quality sets the ceiling on how well Pehchaan can correct names.

### Why we add hard cases and near-duplicates on purpose
If the KB held only easy, distinct names, any matcher would look great. That would be a dishonest test.
Real phone books are messy, so we built the KB to be messy too:
- **Long names** (Ananthapadmanabhan, Thiruvananthapuram) that speech-to-text splits into pieces.
- **English-sounding names** (Kukatpally, Begumpet, Hitech City) that get rewritten as English words.
- **Near-duplicates** (Srinivas Reddy / Sreenivas Goud / Srinivasan Iyer, Ravi Teja / Ravi Tej, Lakshmi / Laxmi).
  A matcher that is too loose will pick the wrong person, so these are where false corrections show up.
- **Honorifics** (Dr., Smt., Sri, Garu, Anna, Ji) that come and go in speech.
- **Cross-type traps**: "Venkataramana Dental Care" is a business, "Dr. Venkataramana" is a person,
  and "Ramulu Tea Stall" is not "Ramulu Anna".

### Why the data is fictional
Hackathon rules (and basic privacy) say: use only data you have permission to use. So every person and business is invented.
Phone numbers follow one fake pattern (`+91-90000-0XXXX`), and the model *rejects* anything else, so a real number
can't sneak in. Place names are public geography, so real names are fine there.

### Key concepts
- **Entity:** one thing we can recognise, here a person, place or business.
- **Canonical name:** the one correct spelling we want in the final transcript.
- **Alias:** another common way of writing the same entity (Laxmi for Lakshmi, Vizag for Visakhapatnam).
- **Surface form:** any text string that refers to an entity, i.e. the canonical name or an alias.
- **Near-duplicate:** two *different* entities whose names look or sound alike.
- **Pydantic validation:** Pydantic checks data against a typed model and raises a clear error if it doesn't fit.
  `Literal["person", "place", "business"]` allows only those exact values.
- **`lru_cache`:** a Python decorator that remembers a function's result, so the second call returns instantly.
- **Negative test:** a test that feeds *bad* data and checks it is rejected. It proves our safety checks work.
- **`language_origin`:** we use "Urdu" for Muslim names and "Biblical" for Christian names. They are name origins,
  which lets Module 5 report accuracy per origin (e.g. "we improved most on Telugu names").

### Questions a judge might ask about this module
- **Why not just put the names in the speech-to-text prompt?** We will test exactly that as baseline 2.
  A prompt can hold only a few names. A real phone book has hundreds, plus places and businesses. A KB scales and lets us score confidence.
- **Is this real user data?** No. Every person and business is fictional, and phone numbers use a fake pattern the code enforces.
  Only public place names are real.
- **How did you make it representative of India?** 12 name origins: 10 regional languages plus Urdu and Biblical
  names (a 13th, Konkani, appears once, for Panaji). There are also English-origin place names.
  Places lean towards Hyderabad because that is where the demo is.
- **Why include confusing near-duplicates?** To test honestly. A correction system's worst failure is
  confidently changing a name to the *wrong* person. Near-duplicates measure that.
- **What stops the data from going bad when someone edits it?** Pydantic plus whole-KB validation runs on every load,
  and 14 tests run with `pytest`, including tests that feed broken data to prove the checks fire.
- **Why can one surface form map to several ids?** Short aliases (like a first name) can belong to more than one person.
  We surface that ambiguity instead of hiding it, and the LangGraph pipeline resolves it with context. Today, no form is ambiguous.
- **How would this work for a real user?** Swap the JSON for their actual phone contacts and saved places (with consent).
  The loader and models stay the same.
