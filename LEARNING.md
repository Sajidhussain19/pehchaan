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

---

## Module 3 — Test set builder

### What we built
- **KB update (mentor feedback).** We added 6 near-identical contact pairs, each with a surname and its own relation:
  Harshit Sharma (gym trainer) / Harshil Patel (accounts colleague), Rohit Chaturvedi / Rohith Reddy,
  Sai Kiran Rao / Sai Kumar Yadav, Anjali Verma / Anjani Mishra, Pranav Joshi / Pranay Reddy,
  Swathi Chowdary / Swati Kulkarni. We also added **Dr. Raju** (family doctor). There is deliberately *no* "Raju Hotel".
  The KB is now 336 entities.
- `data/testset/sentences.json`: **113 sentences** (36 dev / 77 test) with full ground truth.
- `app/testset/models.py` (Pydantic models) and `app/testset/validate.py` (checks against the KB).
- `scripts/build_audio.py`: OpenAI text-to-speech, giving 113 **clean** clips (24 kHz) and 113 **phone-quality** clips (8 kHz).
  It also writes `manifest.json`. That is 9.6 minutes of audio, costing about $0.14.
- `scripts/testset_stats.py`: counts by split, category, direction, behaviour, entity type and difficulty, plus audio minutes.
- `tests/test_testset.py`: 17 tests. The KB tests gained 7 more. The full suite is 39 tests.
- `CLAUDE.md` now lists the 4 **design principles**.

### What ground truth is
Ground truth is the **answer key**: for every sentence, the known correct answer. That means:
- which names it contains, with their KB ids
- what Pehchaan should *do* about them
- which action should come out

We wrote the text first and then made audio *from* that text, so we know exactly what was said.
Every metric later (entity error rate, WER, action accuracy) is "how far is the system's output from this answer key".
The validator checks the answer key itself, because a wrong key would make every number wrong.

### The 4 expected behaviours (one example each)
| Behaviour | Meaning | Example |
|---|---|---|
| **correct** | The name is in the KB, so fix it to the canonical spelling | "Call Dr. Venkataramana…": if speech-to-text writes "Venkat Ramana", fix it |
| **keep** | Unknown name, or no name at all: leave it alone and link nothing | "Call Tejaswini and ask if she reached Nalgonda": neither is in the KB |
| **resolve** | Two contacts look alike, but context picks one | "Ask Harshil to send the invoice": Harshil Patel from the accounts team |
| **clarify** | We can't decide safely, so ask the user | "Call Harshit at 5": did you mean Harshit (gym trainer) or Harshil (accounts)? |

### The five categories and why most are about NOT correcting
| Category | Count | Expected | What it catches |
|---|---|---|---|
| in_kb | 68 | correct | Can we fix names we know? (the headline) |
| out_of_kb | 13 | keep | Inventing a correction: turning a stranger into one of your contacts |
| control | 13 | keep | Changing ordinary words: "The cook at the polling booth…" must not become "Kukatpally" |
| ambiguous | 11 | resolve / clarify | Guessing between Harshit and Harshil instead of using context or asking |
| context_mismatch | 8 | clarify / keep | Linking a matching name that doesn't fit: "Raju Hotel", or "Raju from the bank" on an unknown number |

If we only counted successes, a system that "corrects" everything aggressively would look great.
The four non-correction categories (45 of 113 sentences) measure **wrong corrections**, the mistakes that hurt users most.
Calling the wrong person is worse than asking a question.

### Why a held-out test split matters
While tuning the matcher we will look at results and adjust thresholds. Anything we look at, we slowly overfit to,
even without meaning to. So we split once, up front:
- **dev (36):** we may look at these as much as we like while tuning.
- **test (77):** held out. Used only for the final reported numbers.

The split is **stratified**: each (category, behaviour) group goes about 1/3 to dev and 2/3 to test,
with evenly spaced picks, so both halves contain every kind of sentence. This is how we "can't cheat ourselves".

### Why phone-quality audio matters
Equal AI's assistant listens to **phone calls**, not studio recordings. A phone line:
- carries only 8,000 samples per second (8 kHz)
- keeps only the 300-3400 Hz band, so deep bass and the high "s/sh" detail are cut off
- adds some background noise

Those missing high frequencies are exactly what separates sounds like "s" and "sh", or "th" and "t".
So names get harder to hear. Our phone copies apply the same three steps in numpy/scipy, so we can measure
how speech-to-text, and Pehchaan, cope with realistic call audio.

### Limitation: synthetic audio
The recordings are made by text-to-speech, not by real people. TTS speaks clearly, with no hesitations,
no cross-talk and no real regional accent variety. We rotate 8 voices and 4 speeds and ask for an Indian English accent,
but it is still easier than real calls. **Real human recordings would be harder**, so our absolute error rates are optimistic.
The *comparison* between the three systems is still fair, because all three hear exactly the same audio.

### Key concepts
- **Ground truth / answer key:** the known correct output for each example.
- **Stratified split:** splitting each group separately, so both halves keep the same mix of categories.
- **Text-to-speech (TTS):** a model that turns text into spoken audio. `gpt-4o-mini-tts` also takes an
  `instructions` prompt describing accent and pace.
- **Sample rate:** how many audio measurements per second. TTS gives 24,000 (24 kHz); phone lines carry 8,000.
- **Band-pass filter:** keeps only frequencies between two limits (here 300-3400 Hz) and removes the rest.
- **SNR (signal-to-noise ratio):** how much louder the speech is than the noise, in decibels. We use 25 dB, a light hiss.
- **Manifest:** a list file describing every clip (id, text, voice, speed, paths, duration), so later scripts
  don't need to scan folders.
- **Idempotent script:** running it again changes nothing. `build_audio.py` skips clips that already exist, so a re-run is free.
- **Code-mixing:** Hinglish / Tenglish, Hindi or Telugu words in Latin script inside English ("auto book cheyyi").

### A real problem we hit (and fixed)
`openai==1.59.7` from Module 1 didn't know the TTS `instructions` parameter (`TypeError: unexpected keyword argument`).
We upgraded the SDK to `openai==3.57.0`, which required `anyio>=4.10`. The old FastAPI then showed a deprecation warning
in the test client, so we upgraded `fastapi` to 0.165.0. All versions are pinned again and `pip check` is clean.
Lesson: pinning protects you, but sometimes a new feature means moving the pins together.

### Questions a judge might ask about this module
- **Did you write the sentences to suit your system?** The sentences were fixed before any matcher existed, and the
  final numbers come only from the 77 held-out test sentences.
- **Why include sentences with no names?** To catch false corrections. Control lines check that ordinary words
  ("cook", "lucky", "sunny") are left alone.
- **How do you score "asking"?** Each clarify line lists its candidate ids. A system gets credit only if it asks
  *and* offers the right candidates.
- **Isn't TTS audio too easy?** Yes, it is cleaner than real calls, and we say so. That's why we also test 8 kHz
  phone-quality versions. All three systems hear identical audio, so the comparison stays fair.
- **Why both incoming and outgoing lines?** Equal AI's assistant hears both: callers introducing themselves, and the
  user giving commands. The caller id is extra context ("Raju" from an unknown number is not your doctor).
- **How much did the audio cost?** About $0.14 for 9.6 minutes. Re-running the script costs nothing, because existing clips are skipped.
- **Is any of this real data?** No. All people and businesses are fictional, and phone numbers use a fake pattern.

---

## From name corrector to personal ear (vision upgrade)

### The idea in one line
"AI assistants hear words. Pehchaan understands who you mean." A speech model can learn how "Kukatpally" sounds,
but it can **never** know that *your* doctor is Dr. Venkataramana or that "Amma" means Sarojini Rao.
That knowledge is personal, private and changes over time, so **personal context has to live outside the model**.
That's what Pehchaan is.

### The 4 levels
1. **Misheard names:** "cook at Polly" -> **Kukatpally**. The original goal (Modules 6-8).
2. **Personal references:** "my doctor", "Amma", "my gym trainer", "the usual pharmacy" -> one exact KB entity.
   There is no name to match at all here; the meaning comes from *roles* and *labels*.
3. **Ambiguity:** near-identical names (Harshit / Harshil) or several people with the same role (19 colleagues).
   Use clues; otherwise ask.
4. **Learning:** when the user answers a question ("I meant Harshil"), save it, so next time there's no question.

### The resolution rule: clue -> default -> ask -> remember
The user has **3 doctors**:
| Contact | Roles | Default? |
|---|---|---|
| Dr. Venkataramana | doctor, family doctor, general physician | **yes**, `is_primary_for: ["doctor"]` |
| Dr. Subramanian | doctor, dentist | no |
| Dr. Raju | doctor, eye specialist, ophthalmologist | no |

- **a) Clue:** "Call my doctor, my tooth is paining". "Tooth" points to the *dentist* role, so the answer is **Dr. Subramanian**.
- **b) Default:** "Call my doctor". No clue, so we use the default doctor: **Dr. Venkataramana**.
  (If no default exists, the most recent interaction is a weak tie-breaker.)
- **c) Ask:** "Ask my colleague to join the call". There are 19 colleagues, no default and no clue, so we **ask once**:
  "Which colleague: Srinivas Reddy (backend), Harshil Patel (accounts), …?"
- **d) Remember:** the answer is stored in `data/kb/preferences.json` as
  `{"phrase_pattern": "my colleague", "entity_id": "...", "created_at": "..."}` and used next time.

The order matters. A clue in *this* sentence beats a general default, and a default beats asking.
We ask only when we'd otherwise be guessing, because a wrong call is worse than a question.

### What changed in the data
- **People** gained:
  - `roles`: e.g. `["doctor", "dentist"]`
  - `is_primary_for`: the user's default for a role. At most one per role, enforced by the loader.
  - `family_label`: Amma, Nanna, Akka, Anna, Bhaiya, Thatha, Pinni, Babai, Bava. Each is unique.
  - `last_interaction`: a fake date.
- **New family contacts:** Sarojini Rao (Amma), Ramachandra Rao (Nanna), Aditya Rao (Anna), Rajat Verma (Bhaiya).
- **Exactly 3 doctors for the user.** The other 6 "Dr." contacts became family members' doctors, for example
  Dr. Prameela Rani is Amma's gynaecologist and Dr. Fatima Zehra is your son's paediatrician.
  They keep only their specialty as a role, so "my doctor" never picks Amma's gynaecologist.
  Dr. Raju became the eye specialist, because Dr. Venkataramana is now the family doctor.
- **Businesses** gained `is_usual` + `usual_for`. The usual pharmacy, groceries (kirana), salon and tiffins are marked.
- `preferences.json` starts as `[]`, with a `Preference` model. Module 9 fills it.
- **New lookups:** `get_by_role`, `get_primary_for`, `get_by_family_label`, `get_usual_business`, `load_preferences`.
- **Test set:** a new **reference** category with 19 lines (6 dev / 13 test). Each line lists its `references` with
  `resolution_reason` = clue / primary / family_label / usual / ambiguous. The validator checks each reason against the KB:
  a "primary" answer really is a default, and a "family_label" answer really uses that label.
  Two older lines were reworded ("your sister's skin test", "your father's knee X-ray") and their audio regenerated.
  The total is now 132 lines and 10.8 minutes, at about $0.02 extra.

### A trap worth knowing: "Anna"
"Anna" is both a family label (Aditya Rao, your elder brother) and a respectful suffix in names like
"Ramulu Anna" (the vegetable vendor). "Call Anna" means your brother, but "Ramulu Anna" is a name.
This is exactly why we match whole names before guessing at labels.

### Key concepts
- **Personal reference:** words that point to a person or place *through the user's relationship*, not by name
  ("my doctor", "Amma", "the usual pharmacy").
- **Role:** what a contact is to the user (doctor, dentist, colleague). One person can have several roles.
- **Primary / default:** the contact the user means by a role when nothing else is said.
- **Family label:** the word used at home for a family member (Amma = mother, Nanna = father, Akka = elder sister).
- **Resolution reason:** *why* a reference points where it does. We record it so evaluation can show which kinds work.
- **Preference / learned answer:** a stored (phrase -> entity) answer, so the same question is never asked twice.

### Questions a judge might ask
- **Isn't this just a post-processor?** No speech model can know your contacts; personal context has to live outside
  the model. A speech model can't know that "my doctor" is Dr. Venkataramana. Pehchaan is the layer that holds and uses that context.
- **Why not put the contacts in the speech-to-text prompt?** That is one of our baselines. A prompt can fix *spellings*
  of a few names, but it can't decide that "my doctor" + "tooth" means the dentist, or know when to ask.
- **What happens when it's unsure?** It asks once, with the candidates and their roles, then remembers the answer.
  We never guess an action we're unsure about.
- **How do you know it resolves references correctly?** 19 reference lines in the test set, each with the right entity
  and the *reason* (clue, default, family label, usual, ambiguous). The evaluation reports reference-resolution accuracy separately.
- **Why only 3 doctors?** So "my doctor" is a realistic, testable decision: one default, two specialists that only a clue
  should select. Family members' doctors are stored, but they aren't "my doctor".
- **Doesn't remembering answers risk learning a mistake?** The user explicitly chose the answer, and it is stored with a
  timestamp in a readable file. Wrong or old preferences can be seen and deleted.
- **Is this private?** All data here is fictional. In a real product this context stays on the user's side,
  next to their phone book. It isn't trained into a model.

---

## Plan update after a strict judge review

What changed, and why:
- **A stronger opponent.** Beating plain speech-to-text is easy. The real question is: does Pehchaan beat *one GPT-4o-mini
  call that gets the same contacts and is allowed to ask*? That's baseline (c), built in Module 5. We report per-case
  **wins / ties / losses** against it, because an average can hide where we lose.
- **Simpler matching.** Phonetic + fuzzy with a confidence score, and an LLM only when unsure. Extra methods (BM25,
  embeddings) must *earn* their place on dev results. Fewer parts are easier to explain and debug.
- **Never hide what was heard.** Every decision shows heard -> resolved -> confidence -> reason. A low-confidence match
  is flagged or asked about, never silently replaced.
- **Separate metrics.** One blended score can hide a dangerous failure, such as calling the wrong person.
  So wrong-target rate, unnecessary questions, over-correction and missed clarifications are each reported on their own.
- **One real action: Remind.** A real stored reminder beats three half-built ones (call/book).
- **Learning needs consent.** "Use X this time" vs "Always use X for '<phrase>'". Only the second is remembered.
- **New test cases:**
  - *unfamiliar near-match*: "Rohan" is not your contact Rohit, so we must not "fix" him into Rohit
  - *stale default*: "my doctor about my eye drops" must go to the eye specialist, even though the default doctor is
    the family doctor
- **Real speakers.** Svarah (AI4Bharat, CC BY 4.0) gives real Indian-accented speech. It mostly has none of our names,
  so it checks that Pehchaan doesn't make real transcripts *worse*. It is gated, so access needs the developer's own
  Hugging Face account and token.

---

## Module 4 — Baseline transcription

### What we built
- `app/stt/transcribe.py`: `transcribe(audio_path, prompt=None)` returns `{text, model, latency_ms, cost_estimate_usd}`.
  It uses `gpt-4o-mini-transcribe` by default and also supports `gpt-4o-transcribe` and `whisper-1`.
  It retries rate limits, timeouts and server errors, waiting 1s, then 2s, then 4s.
- `app/stt/hints.py`: builds the **name-hints prompt** for baseline (b), within a token budget.
- `app/stt/baseline.py` + `scripts/run_baseline.py`: transcribe every clip both ways, **with a cache**.
  Options are `--split`, `--audio`, `--variant`, `--limit` and `--model`.
  It prints the estimated cost before spending anything and the total cost afterwards.
- `scripts/show_errors.py`: lists KB names missing from transcripts, plus the 5 most dramatic mistakes.
- `tests/test_stt.py`: 9 tests with a **fake OpenAI client**, so they never call the real API.
- **Results:** 4 files × 142 clips in `data/results/`. The whole module cost about $0.61.

### What speech-to-text is
Speech-to-text (STT, also called ASR, "automatic speech recognition") turns audio into text.
The model has learned which sounds usually mean which words. When it hears an unfamiliar Indian name, it reaches
for the closest *familiar* words, so "Thirumalai" becomes "the roomer life" and "Anjani" becomes "Aunt Johnny".
It isn't broken; it has simply never been told your names.

### What a prompt / hint does for transcription, and its limits
A transcription **prompt** is text the model reads before listening. If it contains "Kukatpally", the model is more
likely to write "Kukatpally" when it hears something close. In our run, hints cut the missed KB names roughly in half
(44-52% down to 24%). That makes (b) a real competitor, not a straw man.

Limits:
- **Size:** the prompt has a budget.
  - `whisper-1` uses only the last 224 tokens, so **54 of our 340 names** fit.
  - `gpt-4o-mini-transcribe` took our whole KB (about 1,300 tokens). In our test it failed around 21,000 tokens.
  - A real user has hundreds of contacts *plus* every locality and shop they mention, and the prompt competes with
    the audio for the model's context. So **hints don't scale to a whole contact book**. That's part of our argument.
- **Spelling, not meaning:** hints can fix the *spelling* of "Dr. Venkataramana". They can't decide that
  "my doctor + tooth" means the dentist, that "Rohan" is *not* your Rohit, or when to ask.
- **Cost:** the prompt is billed as input tokens on every call. Hints cost about 8× more than plain here (about $0.27 vs $0.03 per pass).

We record how many entities were included vs excluded in each results file (`meta.hint_prompt`), so this is visible.

### Why we test clean vs phone vs real speech
- **Clean (24 kHz TTS):** the best case.
- **Phone (8 kHz, band-pass, noise):** what a call assistant really hears. Plain STT missed **52%** of KB names on phone
  audio vs 44% on clean, because the lost high frequencies blur sounds like "dh" and "gh" ("Madhapur" became "Maghapur").
- **Real speech (Svarah):** real people and real accents. It mostly has none of our names, so it checks that we don't
  make transcripts *worse*. We fetched 40 clips from 40 different speakers (first languages from Kannada to Bodo to
  Kashmiri). Rough WER: **plain 9.5%, hints 6.6%**, and the hints **never inserted a KB name** into a real transcript.
  So, for baseline (b), hints didn't over-correct real speech. Pehchaan must pass the same test.
  Note: the Hugging Face copy of Svarah has no speaker-id column, so our `speaker_id` is the speaker's full profile
  (language | state | district | gender | age | education | job). A distinct profile is very likely a distinct person.

### A finding: code-mixed speech comes back in Indian scripts
"Ravi Teja ko call karo…" came back as "रवी तेजक को कॉल करो…", and "Kukatpally nunchi Begumpet…" came back in Telugu script.
The model detected Hindi or Telugu and switched writing system. Our KB is in Latin script, so a plain text match
finds nothing. Modules 5 and 7 must handle this: transliterate before matching, or force `language="en"`.
Exact-match counts also flag harmless formatting differences ("Father Anthony Raj" vs "Fr. Anthony Raj",
"Sri Venkateshwara" vs "Sri Venkateswara"). Module 5 measures properly.

### Why caching matters for cost
Each results file is keyed by **variant + audio + model**, and every clip id inside it is a "done" marker.
The runner skips done clips and saves after each one. This paid off immediately: the first full run crashed on a
Telugu-script transcript the Windows console couldn't print. We fixed the printing, re-ran, and only the remaining
clips were sent. Nothing was paid twice. Module 5 can re-score these transcripts for free, as often as we like.

### Key concepts
- **ASR / STT:** automatic speech recognition / speech-to-text.
- **Transcription prompt:** text given to the STT model to bias its spelling and vocabulary.
- **Token:** the unit models read text in (about 4 characters of English). Prompt budgets and prices are in tokens.
- **Latency:** time from sending the audio to getting text back (in ms). We record it per clip.
- **Exponential backoff:** after a temporary error, wait 1s, then 2s, then 4s before retrying, so a busy server can recover.
- **Cache:** saved results that let us skip repeat work (and repeat cost).
- **Mock / fake client:** a stand-in object for the OpenAI client in tests, so tests are free and offline.
- **Script (writing system):** Latin, Devanagari and Telugu are different alphabets for writing words.

### Questions a judge might ask about this module
- **Which speech model do you use and why?** `gpt-4o-mini-transcribe`: cheap (about $0.003/min), fast, and accurate.
  The model is a config setting, and `gpt-4o-transcribe` / `whisper-1` work with a flag.
- **Isn't name-hinting enough?** It halved the errors, so we treat it as a serious baseline. But it can't hold a
  growing phone book, and it fixes spelling, not meaning: "my doctor", "Rohan ≠ Rohit", or when to ask.
  The strongest competitor, (c) GPT-4o-mini with the same contacts, comes in Module 5.
- **How much did this cost?** About $0.61 for 568 transcriptions (142 clips × 2 audio kinds × 2 variants), plus a few
  cents of tests. Re-running costs $0 thanks to the cache.
- **Did you tune anything on the test split?** No. We only transcribed. Nothing has been tuned yet, and future tuning uses dev only.
- **Why phone-quality audio?** Equal AI's assistant hears calls. Phone audio made plain STT miss 52% of names vs 44%.
- **What surprised you?** Code-mixed Hindi and Telugu lines come back in Devanagari or Telugu script, so name matching
  must cope with more than one alphabet.

---

## Module 5 — Evaluation framework + strong LLM baseline

### What we built
- `app/eval/decision.py`: the **common decision format**. Every resolver system outputs, per clip:
  - heard transcript and output transcript
  - behaviour
  - entities as *heard -> resolved id -> confidence -> reason*
  - clarify candidates
  - a Remind action (target, place, "HH:MM" time, raw time words)
  - whether an LLM was used, latency and cost
- `app/baselines/llm_resolver.py`: **baseline (c)**, one GPT-4o-mini call per clip with the user's whole personal context.
- `app/eval/metrics.py`: every metric, each with raw counts.
- `app/eval/timeparse.py`: spoken time -> "HH:MM". The test set now stores a hand-reviewed `time_hhmm`.
  Only 20 clips have an unambiguous clock time, so only those are time-scored.
- `app/eval/runs.py`: where outputs live, and the cache rule.
- `scripts/run_llm_baseline.py`: runs baseline (c). It is cached and prints its cost first.
- `scripts/evaluate.py`: scores everything and writes `data/results/report_{split}_{audio}.md/.json`, with win/tie/loss counts.
- `tests/test_eval.py`: 22 tests with hand-made examples and a fake OpenAI client.

### The strong LLM baseline, and why it's fair
Judges will ask: *"Why not just give one LLM the user's contacts?"* Baseline (c) is exactly that, done properly:
- **Same information as Pehchaan:** the plain transcript, the call context (outgoing, or incoming from a saved or
  unknown number), and the whole KB (about 33,000 characters): contacts with relation, roles, default-for, family
  label and notes; businesses with area and "usual for"; places.
- **The same rules, written into its prompt:** clue beats default; default beats asking; ask when two fit equally;
  never invent; keep unknown names; "Raju from the bank" on an unknown number is not your Dr. Raju.
- **Restricted output ids:** structured output with a **strict JSON schema** whose id fields are an enum of the
  340 real KB ids. The model physically cannot output an invented id. This is fair because either system could do
  it, and it only *helps* the baseline: it removes typo'd ids.
- **Frozen prompt:** written once, *before* looking at results. We didn't tweak it to fix individual clips.
  Doing that would quietly tune the opponent, or our test, to the data.

### How the scoring works
- **Transcript metrics** apply to any system that outputs text:
  - **entity accuracy:** a KB name counts only if it appears exactly, ignoring case and punctuation. "doctor" = "Dr."
  - **WER** (word error rate, via `jiwer`) = (substituted + deleted + inserted words) / reference words.
  - **over-correction:** on clips where nothing should be linked (control, out_of_kb, real speech, unfamiliar
    near-match), did a KB entity appear that wasn't said? This covers both the text and the system's links.
- **Decision metrics** apply to (c) and, later, Pehchaan:
  - behaviour accuracy
  - exact action target (person **and** place)
  - time accuracy
  - **wrong-target rate:** acted on the wrong entity, or used a non-existent id. It never crashes; it just counts as wrong.
  - unnecessary questions
  - missed clarifications
  - right clarify candidates
  - reference resolution
  - no-LLM rate, latency, cost
- **One rule everywhere:** a *clarify* decision takes **no action yet**, even if the system also filled in a target,
  because the reminder is only created after the user answers.
- **Win / tie / loss:** each clip gets one outcome label: its worst problem (wrong target, then over-correction,
  then missed clarification, then other errors, then ok). The two systems' labels are then compared.
  If one system only outputs text, both are compared on text only, so like is compared with like.

### Dev results (45 synthetic clips × clean + phone, + 14 real clips)
| | (a) plain | (b) hints | (c) LLM baseline |
|---|---|---|---|
| entity accuracy | 41/64 = 64% | 49/64 = 77% | 55/64 = 86% |
| WER | 277/1163 = 24% | 248/1163 = 21% | 198/1163 = 17% |
| over-correction | 0/34 | 0/34 | 1/34 = 3% |
| behaviour accuracy | - | - | 85/104 = 82% |
| exact action target | - | - | 40/52 = 77% |
| wrong-target rate | - | - | 9/104 = 9% |
| unnecessary questions | - | - | 2/92 = 2% |
| missed clarifications | - | - | **7/8 = 88%** |
| reference resolution | - | - | 8/14 = 57% |
| latency / cost per call | - | - | ~1.5 s / ~$0.001 |

What this teaches us:
- (c) is genuinely strong at **spelling**. It beats the hints on entity accuracy and WER.
- But it **guesses instead of asking**. With "Call Harshit at 5", it picks Harshit. With "Remind me to call Pranav", it picks Pranav Joshi.
- It **invents fits**. "Raju Hotel" became an unrelated fancy store, and on phone audio "Nalgonda" became Hyderabad.
- It **lets the default beat the clue**: "my doctor, my tooth is paining" went to the family doctor.

These are the exact failure modes Pehchaan's design targets. Now we have to *show* it does better.

### Why we don't tune on test results
If we look at test results and then change Pehchaan (a threshold, a rule, a prompt), the test set has quietly
become training data. The next test score is then optimistic, because we fitted it. So all tuning uses **dev**.
`evaluate.py` refuses the test split unless you pass `--final`, warns you, and logs every test run in
`data/results/test_runs.log`, so we (and judges) can see how many times it was looked at.

### Key concepts
- **Structured output / strict JSON schema:** the API forces the model's answer to match a schema exactly.
  An `enum` limits a field to a fixed list of values, here the real KB ids.
- **WER:** word error rate, the standard speech-to-text metric.
- **Over-correction:** "fixing" something that wasn't broken, e.g. turning a stranger into one of your contacts.
- **Wrong target:** acting on the wrong entity. The worst error, because the assistant confidently does the wrong thing.
- **Missed clarification vs unnecessary question:** guessing when you should ask, vs asking when you didn't need to.
  A good system keeps both low.
- **Prompt caching:** OpenAI automatically discounts a repeated prompt prefix. We put the big, identical context
  first, so 98 calls cost about $0.095 instead of the estimated $0.15.
- **Held-out test split / data leakage:** test data must not influence any design decision, or its scores stop being honest.

### Questions a judge might ask about this module
- **Isn't your LLM baseline a strawman?** No. It gets the same context and the same rules, written explicitly into
  its prompt. Strict-schema output restricts it to real ids. Its prompt was frozen before seeing results.
  It's genuinely good: 86% entity accuracy vs 77% for hints.
- **Why not just use that baseline as the product?** On dev it guessed in 7 of 8 cases where it should have asked,
  acted on the wrong entity in 9% of clips, and resolved only 57% of personal references.
  It also needs an LLM call on every clip (~1.5 s, ~$0.001).
- **Why so many metrics instead of one score?** A blended score hides the dangerous errors. A system can look 90%
  "accurate" and still call the wrong person. Each metric answers one question and shows raw counts.
- **How do you score a question ("did you mean…")?** Behaviour must be clarify, no action is taken, and the offered
  candidates must include the right people (`clarify_candidates_ok`).
- **What about time?** Spoken times are normalised to "HH:MM" with one shared rule. Ambiguous ones ("at 5") are
  never scored, because we don't guess AM or PM on anyone's behalf.
- **Have you looked at the test split?** Not yet. `data/results/test_runs.log` doesn't exist. All numbers here are dev.
- **How much did this cost?** About $0.10 for baseline (c) on dev, plus a few cents of smoke tests.

---

## Modules 6+7 — Candidate spans + phonetic matching (no LLM, no decisions)

### What we built
- `app/match/translit.py`: Devanagari and Telugu script -> Latin letters ("रवी तेजक" -> "ravii tejak").
- `app/match/phonetic.py`: `normalise`, `indian_phonetic_key` (Indian-English sound rules), Double Metaphone
  keys (the `metaphone` library), and `phonetic_similarity` (0-1).
- `app/match/spans.py`: tokens with character positions; every 1-4 word span with context features;
  personal-reference phrases.
- `app/match/candidates.py`: scores KB entities per span, keeps the top 3, removes overlapping spans.
- `app/match/config.py`: every weight in one place: `INITIAL`, then `TUNED` on dev.
- `data/lexicon/common_english_words.txt`: about 3,300 common English words, plus everyday Hindi/Telugu words in Latin script.
- `scripts/inspect_candidates.py` and `scripts/eval_candidates.py`, which runs on the dev split only.
- `tests/test_match.py`: 26 tests. The whole suite is 118 tests.

### How it works, step by step
1. **Tokenise** the transcript, remembering each word's character position, so every span can point back into the text.
   Indian-script words are transliterated first.
2. **Personal references** are found by exact phrase rules: "my <role>" (my doctor, my son's teacher),
   "call/ask/tell **the** <role>" (the electrician), family words (Amma, Nanna, Akka, Bhaiya…), "the usual <category>"
   and "same <x> as last time". Each one gets **all** fitting entities from the loader: "my doctor" gives
   3 doctors, with the default marked. These spans always keep their words.
3. **Name spans:** every run of 1-4 words, skipping runs made only of tiny words like "the" or "to". Each span gets context
   features: a place word before it ("in", "at", "from", "nunchi") hints place/business; "call", "tell", "Dr",
   "garu", "anna", "here" hint person; capitalisation; and whether every word is common English.
4. **Forms:** every way a KB entity can be written. That's the name, the aliases, the name without honorifics
   ("Venkataramana"), and for people the first name and first + surname. About 1,500 forms in all.
5. **Shortlist, then score:** a fast RapidFuzz search on sound keys picks about 25 forms, plus any form with the
   *same* Double Metaphone code. Each is then scored:
   `base = 0.45·sound + 0.55·spelling`, minus a length penalty, minus a common-English penalty (unless the text is
   exactly that name), plus a capital bonus. The best form per entity counts, and the top 3 entities are kept.
6. **Non-max suppression:** sort the spans by best score, keep a span only if it doesn't overlap one already kept,
   and on equal scores prefer the longer span.
7. **Output:** `Span{start, end, heard_text, kind, type_hint, candidates[top 3: entity, score, sound, spelling, reasons], margin}`.
   About **7-9 ms per sentence** on average and 20-40 ms at worst, with no LLM.

### The sound rules (examples)
Spaces are removed first, because names get split into English words ("Aunt Johnny" = "auntjohnny"). Then:
- **th→t, dh→d, bh→b, ph→f, kh→k, gh→g:** "the roomer" ~ "Thirumalai", "Madhapur" ~ "Madapur"
- **hard c / ck / q → k:** "cook at" ~ "Kukat", "Cockatiel" ~ "Kakatiya", "Qureshi" ~ "Kureshi"
- **w→v, z→j, sh→s:** "Warrier" ~ "Varrier", "Zehra" ~ "Jehra", "Sharma" ~ "Sarma"
- **aa→a, ee/ii→i, oo/uu→u, final y→i:** "Keerthi" ~ "Kirthi", "the roomer" ~ "tiru", "Johnny" ~ "Joni"
- **silent h after a vowel, trailing h, double letters → single:** "Shah" ~ "Sha", "Kukatpally" ~ "Kukatpali"

Double Metaphone is a classic English sound code and gives a second opinion: "cook at polly" and "Kukatpally" both
become **KKTPL**. Our Indian key knows Indian spellings; Metaphone knows English spelling habits. We blend them 60/40.

### Bugs the dev evaluation caught (and what we changed)
- **"The cook at the polling booth" became a reference to the user's cook.** "the <role>" now only counts
  after a request verb ("Call **the electrician**"). "my <role>" always counts.
- **"said" → "Sid"** (an alias of Siddharth) scored 0.78. Forms of 3 letters or fewer now match only exactly, and
  the common-English penalty applies in full unless the text spells that exact name.
- **"father's" → Fr. Anthony Raj, "Doctor" → Dr. Raju.** The alias "Father Anthony Raj" had produced the first name
  "father". "doctor", "father" and "sister" are now stripped as honorifics.
- **Hindi "कल तक" (*kal tak*, "by tomorrow") → Cuttack (0.82).** Added everyday Hindi/Telugu words to the
  common-word list.
- **Telugu "నాన్న" ("naanna") missed the family label "Nanna".** Family words are now compared by sound key, and
  "Amas" (STT's version of "Amma's") also matches.
After these fixes, high-confidence wrong candidates on in-KB dev clips went from **15/79 to 0/60**, and reference
recall from **10/14 to 13/14**.

### Tuning, honestly (dev only)
| | INITIAL weights | TUNED weights |
|---|---|---|
| recall@1 / recall@3 (all KB names) | 64/64 / 64/64 | 64/64 / 64/64 |
| recall@1 / recall@3 (misheard names only) | 23/23 / 23/23 | 23/23 / 23/23 |
| reference recall | 13/14 | 13/14 |
| false-alarm clips (≥ 0.80 on keep-type clips) | 2/34 (both "Sravanthi" -> Sravani) | 2/34 |
| margin of correct top candidate (mean) | 0.26 | **0.33** |
| best wrong score on keep-type clips (mean) | 0.56 | **0.42** |

**Recall on dev was already 100%,** so tuning couldn't improve it. The grid was decided by *separation*: right
answers stand out more, and clips with no KB names look less tempting. Both make Module 8's thresholds safer.
What changed:
- sound 0.6 → 0.45 and spelling 0.4 → 0.55, because sound alone flattered wrong names
- length penalty 0.3 → 0.5
- type bonus 0.08 → 0
- common penalty 0.25 → 0.15
- minimum span score 0.55 → 0.6

**Caveat we are not hiding.** The dev split has only 23 misheard names, and all were found. That's too few to tune
recall. While inspecting the 5 dramatic mistakes (as asked), we saw that 4 of them are **test** clips. There, the tuned
weights drop "sweetie" → Swati and "a bit" → Abids below the 0.6 span cut-off, and Anjani falls to #3 behind
"Anthony". We did **not** change anything because of that, since it would be tuning on test. The right fix is more hard
mishearings in **dev** (new TTS sentences), so future tuning can see them.

### Key concepts
- **Span / n-gram:** a run of n consecutive words. We try n = 1-4, because names get split.
- **Phonetic key:** a spelling-independent code for how something sounds.
- **Double Metaphone:** a well-known phonetic algorithm for English spelling. "Double" means it can give two codes.
- **RapidFuzz ratio:** a 0-100 string similarity based on edit distance (how many edits turn one string into the other). It's very fast.
- **Transliteration:** writing words from one script in another (Devanagari -> Latin), not translating them.
- **Recall@k:** is the right answer among the top k candidates?
- **False alarm:** a confident candidate where nothing should be linked, i.e. an over-correction risk.
- **Margin:** best score minus second-best. A small margin means two candidates are too close to call, so Module 8 should ask.
- **Non-max suppression (NMS):** keep the best of overlapping guesses and drop the rest (a term borrowed from object detection).

### Questions a judge might ask
- **Why not just ask an LLM to find the names?** It costs ~1.5 s and money per call, and baseline (c) shows it
  guesses. This layer finds candidates in about 8 ms with no API call, and shows *why* (sound, spelling, context).
  Module 8 uses an LLM only for the unsure cases.
- **How do you handle "Kukatpally" → "cook at Polly"?** Spans cross word boundaries and spaces are removed before
  comparing sounds. "cook at polly" and "Kukatpally" even get the same Metaphone code.
- **What stops "lucky" or "the cook" from becoming a contact?** A common-English penalty, a length penalty, exact-only
  matching for very short names, and "the <role>" only counting after a request verb. Control sentences produce no confident candidates.
- **What about Hindi or Telugu output from speech-to-text?** A built-in transliteration table turns it into Latin
  letters first, so "कल तक" can be recognised as ordinary Hindi ("by tomorrow"), not Cuttack.
- **Are your recall numbers too good?** On dev, yes, partly. Many names were transcribed correctly, so we also report
  the 23 *misheard* ones separately. And we say plainly that dev has too few hard mishearings to tune recall.
- **Did you tune on the test set?** No. `eval_candidates.py` only reads dev. We looked at 4 test clips only to show
  the dramatic examples, and changed nothing because of them.
