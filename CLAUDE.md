# CLAUDE.md — Project brief for Pehchaan

This file gives every future Claude Code session the full context of this project.
Read it before doing any work.

## Context
28-hour solo hackathon: **Builders 2026 by OpenAI x Equal AI, Hyderabad**.
The developer is an AI engineer who is still learning, so this is a **LEARN + BUILD** project.
We build in 10 modules, **one module per session**. Never build pieces of a later module early.

## The project
- **Name:** Pehchaan (Hindi for "recognition / identity")
- **Tagline:** "Pehchaan — gets Indian names right."
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

The corrected transcript becomes a structured action (call / book / remind).

### Proof
The same 60-80 recordings are run through:
1. plain OpenAI speech-to-text
2. speech-to-text with name hints in the prompt
3. our system

Headline metric: **entity error rate**. We also report WER and action accuracy.

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
