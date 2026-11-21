# CLAUDE.md — Project brief for Pehchaan

This file gives every future Claude Code session the full context of this project.
Read it before doing any work.

## Context
28-hour solo hackathon: **Builders 2026 by OpenAI x Equal AI, Hyderabad**.
The developer is an AI engineer who is still learning, so this is a **LEARN + BUILD** project.
We build in 10 modules, **one module per session**. Never build pieces of a later module early.

## The project
- **Name:** Pehchaan (Hindi for "recognition / identity")
- **Tagline:** "Pehchaan — gets Indian names right." / "AI assistants hear words. Pehchaan understands who you mean."
- **Track:** "Build Challenging — Voice AI for India" (theme idea: Indian names and entities)

### Problem
General speech-to-text models mis-transcribe Indian names, places and businesses
(e.g. "Kukatpally" -> "cook at Polly", "Dr. Venkataramana" -> "doctor Venkat Ramana").
This breaks call summaries and actions in voice assistants like Equal AI's AI call assistant.

### Solution (updated after the judge review)
A layer that runs after speech-to-text. It finds name/place spans and personal references in the transcript and
resolves them against the user's knowledge base (contacts + Indian places + local businesses).
- **Matching is simple:** phonetic + fuzzy matching with a confidence score. An LLM is used **only when unsure**.
  No BM25 or embeddings unless they measurably improve the **dev** results.
- **Routing:** a small LangGraph pipeline decides:
  - high confidence -> resolve
  - unsure -> the LLM checks with context, or we clarify
  - unknown -> keep the original and flag it
- **Personal references** ("my doctor", "Amma", "the usual pharmacy") use the resolution rule below.
- **Never hide what was heard:** every resolved entity shows *heard text -> resolved entity -> confidence -> reason*.
  Low confidence means flag or clarify, **never a silent replace**.
- **One real action only: Remind.** It creates a real stored reminder (person, time, place, heard vs resolved),
  listed and openable in the UI. Call and Book are **out of scope**. The test set still annotates
  call/book/message targets, and those targets are scored for action-target accuracy.

## Vision: "the personal ear"
Pehchaan is not just a name corrector. It understands WHO or WHAT the user means, using personal context.

**Pitch:** "AI assistants hear words. Pehchaan understands who you mean. No speech model can know YOUR contacts —
personal context has to live outside the model."

### The 4 levels
1. **Misheard names:** "cook at Polly" -> Kukatpally
2. **Personal references:** "my doctor", "Amma", "my gym trainer", "the usual pharmacy" -> the exact KB entity
3. **Ambiguity:** near-identical names or several matching people -> use clues, else ask
4. **Learning:** remember the user's answer, so the same request resolves automatically next time

### Resolution rule (for references and ambiguity, in this order)
a) **Clue in the sentence**, e.g. "tooth" -> dentist, "invoice" -> the accounts colleague.
   A clue beats a stale default ("my doctor about my eye drops" -> eye specialist, not the family doctor).
b) **The user's default / primary entity** for that role (e.g. the contact marked primary family doctor),
   or the most recent interaction
c) **Still unclear -> ask once (clarify)**, listing the candidates with their roles
d) **Learning needs consent.** A clarify answer offers two buttons:
   - **"Use X this time"**: only this reminder; nothing is learned
   - **"Always use X for '<phrase>'"**: saves a preference in `data/kb/preferences.json`
   Only the second one changes future behaviour.

Example, the user has 3 doctors (Dr. Venkataramana = family doctor and default, Dr. Subramanian = dentist,
Dr. Raju = eye specialist):
- "Call my doctor, my tooth is paining" -> Dr. Subramanian (clue)
- "Call my doctor" -> Dr. Venkataramana (default)
- "Ask my colleague to join" -> 19 colleagues, no default, no clue -> ask

KB support: person context has `roles`, `is_primary_for`, `family_label` and `last_interaction`;
business context has `is_usual` and `usual_for`.

## Proof: baselines and metrics (updated after the judge review)
**Baselines.** All are run on the same recordings, and we report on the **held-out test split**:
- (a) plain speech-to-text
- (b) speech-to-text with name hints in the prompt
- (c) **STRONG LLM BASELINE** (built in Module 5): one GPT-4o-mini call given the raw transcript plus the same
  contacts, roles, defaults, places and businesses, and allowed to answer "clarify"
- (d) Pehchaan

We report **per-case wins / ties / losses of Pehchaan vs (c)**, not only averages.

**Metrics.** Each is reported separately; there is never one blended number.
- exact action-target accuracy
- wrong-target rate
- unnecessary-question rate
- over-correction rate
- missed-clarification rate
- reference-resolution accuracy
- latency and cost per call: the whole interaction, up to the reminder being created
- how many cases Pehchaan resolves WITHOUT any LLM call
- WER and entity error rate, as supporting numbers

**Test data:** `data/testset/` (synthetic TTS, clean + phone quality) plus `data/realspeech/`
(real Indian-accented speakers from AI4Bharat Svarah, CC BY 4.0). The real clips test the main safety question:
does Pehchaan make real transcripts WORSE (over-correction)?

## Demo plan
- Keep the two-contact-books doctor demo **short**.
- **Centrepiece:** a held-out clip where Pehchaan and baseline (c) actually diverge, shown with the overall
  win / tie / loss counts.
- Live mic ("try it yourself").
- One **honest failure case**.
- Later polish (only after core modules work): a call-screen UI with heard -> resolved, reminder cards,
  live learning with consent, and latency and cost per call.

**Cut list (cut in this order if short of time):** extra matching methods -> LLM-as-judge -> deployment polish.
**NEVER cut:** strong-baseline evaluation, the real Remind action, the live mic, held-out results.

Judges score: a working end-to-end demo, how AI-native it is, presentation and craft.

## Design principles
1. The knowledge base is the user's personal context (hundreds of entries), not all names in India.
   People and businesses come from the user; places come from a public list of Indian localities.
2. Fix what we know, ask when unsure, leave alone what we don't know. Never invent a name.
3. A name matching is not enough; it must fit the context. (Dr. Raju the doctor is not "Raju Hotel".
   The same name from an unknown caller is a different person.)
4. When the top two matches are too close (Harshit vs Harshil) and context doesn't separate them,
   ask instead of guessing. A wrong action is worse than a question.
5. A name one sound away from a contact ("Rohan" vs contact "Rohit") may simply be someone else:
   keep or clarify, never silently resolve.
6. Never hide what was heard. Always show heard -> resolved -> confidence -> reason.

## Tech stack
Python 3.11+ (venv uses 3.12), FastAPI, Pydantic, Uvicorn, OpenAI SDK (transcription, TTS, GPT-4o-mini),
LangGraph (only for the routing pipeline), RapidFuzz, a phonetic library, numpy/scipy/soundfile (audio),
pytest, a simple HTML/JS page served by FastAPI. Deploy on AWS EC2 later.
(BM25 / embeddings only if they measurably help on dev.)

## The 10 modules
1. Setup  (DONE)
2. Knowledge base  (DONE)
3. Test set builder  (DONE)
4. Baseline transcription: baselines (a) and (b)  (DONE)
5. Evaluation, including the strong LLM baseline (c) and win/tie/loss reporting  (DONE)
6. Entity span detection  (DONE, with Module 7)
7. Matching engine (phonetic + fuzzy + confidence)  (DONE)
8. LangGraph correction pipeline  (DONE: app/decide, dev results in LEARNING.md)
9. Remind action + API (real stored reminders, learning with consent, latency/cost per call)  (DONE: app/api, app/store, data/kb/books; final held-out run tagged final-eval-v1)
10. Demo UI + live mic + AWS deploy

## Decision-logic freeze (since Module 9, before the final held-out run)
- Do NOT change logic or thresholds in `app/match/`, `app/decide/`, `data/lexicon/` or the base KB files
  (`data/kb/contacts|places|businesses.json`) unless the developer EXPLICITLY approves.
- `tests/test_freeze.py` checks their fingerprints (`data/results/frozen_logic.json`).
- If a change is ever approved after the final run: repeat the final run (`--final`), disclose the change in README
  ("Decision-logic freeze" section), then re-record with `python scripts/freeze_logic.py`.
- Never tune on test results. The final held-out run happens once (Module 9) and is tagged `final-eval-v1`.

## Repo layout
- `app/` — FastAPI app and all project code (`main.py`, `config.py`, `kb/`, `testset/`, `stt/`, `match/`, `decide/`, `api/`, `store/`)
- `data/kb/books/` — demo contact books A and B (overlays on the base KB; learned preferences per book are git-ignored)
- `data/kb/` — knowledge base files (Module 2) + `preferences.json`
- `data/testset/` — test sentences + synthetic audio (Module 3)
- `data/realspeech/` — real-speaker clips (Svarah sample) + manifest
- `data/results/` — transcripts and evaluation reports
- `scripts/` — runnable scripts (e.g. `check_openai.py`)
- `tests/` — pytest tests
- `web/` — demo page (Module 10)

## Hackathon rules (must respect)
- All code must be written fresh in this repo. Do not copy code from the developer's other projects. Open-source libraries are fine.
- Keep it simple. No extra frameworks, no MCP, no multi-agent systems. The developer must be able to explain every part to judges.
- **Never read, print or commit the `.env` file or any API key.**

## How to work (LEARNING MODE)
- Comment code generously. Every file starts with a short block saying what it does and why it exists in the project.
  Inside the file, comment each important step in plain English (what it does + why).
- After building, explain what was made in simple words, as if teaching a beginner.
- Append a section for the module to `LEARNING.md`: what we built, how it works, key concepts (explain any new term),
  and "Questions a judge might ask about this module" with short answers.
- Run everything yourself and fix errors before saying a module is done.
- End with: the list of files created, the exact commands the developer should run to check it works, and what they should see.

## Common commands (Windows PowerShell)
```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -v
uvicorn app.main:app --reload        # then open http://127.0.0.1:8000/health
python scripts/check_openai.py
```
