# Pehchaan

**Pehchaan — gets Indian names right.**

> A correction layer for speech-to-text. It fixes mis-heard Indian names, places and businesses,
> so voice assistants can take the right action.

*Built solo for Builders 2026 by OpenAI x Equal AI, Hyderabad. Track: Build Challenging — Voice AI for India.*

## The problem

General speech-to-text models often get Indian names wrong:

| What was said        | What speech-to-text wrote |
|----------------------|---------------------------|
| Kukatpally           | cook at Polly             |
| Dr. Venkataramana    | doctor Venkat Ramana      |

One wrong name breaks everything after it. The call summary is wrong, and "call Dr. Venkataramana"
can't be turned into a real action. Voice assistants like Equal AI's call assistant feel this directly.

## The idea (in one breath)

After speech-to-text, Pehchaan finds the name and place spans in the transcript. It matches them
against a knowledge base (your contacts + Indian places + local businesses) using phonetic, fuzzy,
BM25 and embedding matching, then scores its confidence:
**high confidence -> replace, unsure -> an LLM checks with context, unknown -> keep and flag.**
The corrected transcript becomes a structured action: call / book / remind.

## Setup (Windows PowerShell)

Requires Python 3.11+ (we use 3.12).

```powershell
# 1. Create and activate a virtual environment
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your OpenAI key: copy the template, then edit .env and paste your key
copy .env.example .env

# 4. Check the key works
python scripts/check_openai.py

# 5. Run the server, then open http://127.0.0.1:8000/health
uvicorn app.main:app --reload

# 6. Run the tests
pytest -v
```

On macOS/Linux, activate with `source venv/bin/activate` and copy with `cp .env.example .env`.

## Project layout

```
app/            FastAPI app and all project code
data/kb/        knowledge base (contacts, places, businesses)
data/testset/   test sentences + audio
data/results/   transcripts and evaluation reports
scripts/        runnable scripts
tests/          pytest tests
web/            demo page
```

## How it works
*Coming in later modules (6-9).*

## Results: entity error rate, WER, action accuracy
*Coming in Module 5.* We will compare plain speech-to-text, speech-to-text with name hints, and Pehchaan
on the same 60-80 recordings.

## Demo
*Coming in Module 10.*

## Deployment (AWS EC2)
*Coming in Module 10.*
