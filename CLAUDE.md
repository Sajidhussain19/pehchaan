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

### Solution
A correction layer that runs after speech-to-text. It finds name/place spans in the transcript and
matches them against a knowledge base (personal contacts + Indian places + local businesses).
Matching is a hybrid of phonetic, fuzzy, BM25 and embedding methods, followed by reranking and a confidence score.
Then a LangGraph pipeline decides what to do:
- high confidence -> replace
- unsure -> an LLM checks the candidate using the context
- unknown -> keep the original and flag it

It also resolves personal references ("my doctor", "Amma", "the usual pharmacy") with the resolution rule below.
The corrected transcript becomes a structured action (call / book / remind / message).

## Vision: "the personal ear"
Pehchaan is no longer just a name corrector. It understands WHO or WHAT the user means, using personal context.

**Pitch:** "AI assistants hear words. Pehchaan understands who you mean. No speech model can know YOUR contacts —
personal context has to live outside the model."

### The 4 levels
1. **Misheard names:** "cook at Polly" -> Kukatpally
2. **Personal references:** "my doctor", "Amma", "my gym trainer", "the usual pharmacy" -> the exact KB entity
3. **Ambiguity:** near-identical names or several matching people -> use clues, else ask
4. **Learning:** remember the user's answer, so the same request resolves automatically next time

### Resolution rule (for references and ambiguity, in this order)
a) **Clue in the sentence**, e.g. "tooth" -> dentist, "invoice" -> the accounts colleague
b) **The user's default / primary entity** for that role (e.g. the contact marked primary family doctor),
   or the most recent interaction
c) **Still unclear -> ask once (clarify)**, listing the candidates with their roles
d) **Store the answer as a preference** (`data/kb/preferences.json`) and use it next time

Example, the user has 3 doctors (Dr. Venkataramana = family doctor and default, Dr. Subramanian = dentist,
Dr. Raju = eye specialist):
- "Call my doctor, my tooth is paining" -> Dr. Subramanian (clue)
- "Call my doctor" -> Dr. Venkataramana (default)
- "Ask my colleague to join" -> 19 colleagues, no default, no clue -> ask

KB support: person context has `roles`, `is_primary_for`, `family_label` and `last_interaction`;
business context has `is_usual` and `usual_for`. The test set has a `reference` category.

### Demo upgrades (only AFTER core Modules 4-8 work)
- Module 9: learning from corrections shown live; latency and cost per call.
- Module 10: a call-screen UI with before/after names and action cards; a "try it yourself" mic button.
- Optional: Hindi/Telugu code-mixed names.

### Proof
The same recordings (data/testset: 132 lines, 10.8 min) are run through:
1. plain OpenAI speech-to-text
2. speech-to-text with name hints in the prompt
3. Pehchaan

Evaluation reports **separate scores for each of the three systems**:
- entity accuracy (headline: entity error rate)
- over-correction rate
- ambiguity handling
- context-mismatch handling
- reference resolution accuracy
- action accuracy
- latency
- cost

WER is also reported.

Judges score: a working end-to-end demo, how AI-native it is, presentation and craft.

## Design principles
1. The knowledge base is the user's personal context (hundreds of entries), not all names in India.
   People and businesses come from the user; places come from a public list of Indian localities.
2. Fix what we know, ask when unsure, leave alone what we don't know. Never invent a name.
3. A name matching is not enough; it must fit the context. (Dr. Raju the doctor is not "Raju Hotel".
   The same name from an unknown caller is a different person.)
4. When the top two matches are too close (Harshit vs Harshil) and context doesn't separate them,
   ask instead of guessing. A wrong action is worse than a question.

## Tech stack
Python 3.11+ (venv uses 3.12), FastAPI, Pydantic, Uvicorn, OpenAI SDK (transcription, TTS, GPT-4o-mini,
embeddings), LangGraph (only for the routing pipeline), RapidFuzz, a phonetic library, rank_bm25,
pytest, a simple HTML/JS page served by FastAPI. Deploy on AWS EC2 later.

## The 10 modules
1. Setup  (DONE)
2. Knowledge base  (DONE)
3. Test set builder  (DONE)
4. Baseline transcription
5. Evaluation
6. Entity span detection
7. Matching engine
8. LangGraph correction pipeline
9. Action extraction + API
10. Demo UI + AWS deploy

## Repo layout
- `app/` — FastAPI app and all project code (`main.py`, `config.py`)
- `data/kb/` — knowledge base files (Module 2)
- `data/testset/` — test sentences + audio (Module 3)
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
