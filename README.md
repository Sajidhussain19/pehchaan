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

## Knowledge Base

Pehchaan corrects names by matching them against things *you* actually know. Those live in `data/kb/`:

| File | What | Count |
|------|------|-------|
| `contacts.json`   | personal contacts: doctors, family, colleagues, drivers, shopkeepers | 130 |
| `places.json`     | Hyderabad localities (heavy), plus cities and localities across India | 145 |
| `businesses.json` | local clinics, pharmacies, restaurants, salons, schools, shops | 61 |

Each entry has a canonical spelling, common alternate spellings (`aliases`), a language of origin
(Telugu, Tamil, Kannada, Malayalam, Hindi, Marathi, Bengali, Punjabi, Gujarati, Odia, Urdu, Biblical, ...),
a difficulty, and context (relation + phone for people, city/state for places, category + area for businesses).
It deliberately includes **hard cases**: long names (*Thiruvananthapuram*), English-sounding places
(*Kukatpally*, *Begumpet*), near-duplicates that must not be confused (*Srinivas Reddy / Sreenivas Goud /
Srinivasan Iyer*, *Ravi Teja / Ravi Tej*, and six near-identical pairs such as *Harshit Sharma / Harshil Patel*), and honorifics (*Dr., Smt., Garu, Anna, Ji*).

**All people and businesses are fictional** and every phone number uses the fake pattern `+91-90000-0XXXX`.
Only public place names are real. We use only data we have permission to use.

```powershell
python scripts/kb_stats.py   # summary: counts by type / language / difficulty
```

## Test Set

The "same recordings" every system is compared on live in `data/testset/`: **113 short phone-call and voice-note lines**.
They include incoming calls and outgoing commands, some Hinglish / Tenglish, and **9.6 minutes of audio**.
Each line has ground truth: the KB ids of the names in it, what Pehchaan should do, and the expected action
(call / book / remind / message / none).

**5 categories.** Most of the non-headline ones exist to catch *wrong* corrections, not just count successes:

| Category | Lines | Example | Expected |
|---|---|---|---|
| `in_kb` | 68 | "Call Dr. Venkataramana and ask if he is free this evening." | correct |
| `out_of_kb` | 13 | "Call Tejaswini and ask if she reached Nalgonda." | keep |
| `control` | 13 | "The cook at the polling booth said lunch is ready." | keep |
| `ambiguous` | 11 | "Ask Harshil to send the invoice" / "Call Harshit at 5." | resolve / clarify |
| `context_mismatch` | 8 | "Book a table at Raju Hotel…" / unknown caller: "I'm Raju from the bank" | clarify / keep |

**4 expected behaviours:** **correct** (fix a known name), **keep** (leave unknown names and ordinary words alone),
**resolve** (pick the right one of two look-alike contacts using context), **clarify** (ask the user instead of guessing).

**Dev / test split:** 36 **dev** lines may be inspected while tuning. 77 **test** lines are held out and used only
for the final numbers. The split is stratified, so every category appears in both.

**Audio:** every line was spoken by OpenAI text-to-speech (`gpt-4o-mini-tts`, Indian English accent, 8 rotating voices,
4 speeds). Each line comes in two versions:
- `audio/clean/` (24 kHz)
- `audio/phone/`: 8 kHz, 300-3400 Hz band-pass, light noise, i.e. what a phone call actually carries

`manifest.json` lists every clip. The audio (36 MB) is committed so you can listen to it.

**Honest limitation:** this is *synthetic* TTS audio. Real human recordings, with hesitations, background chatter
and strong regional accents, would be harder, so absolute error rates here are optimistic. The comparison between
systems is still fair, because every system hears exactly the same audio.

```powershell
python -m app.testset.validate     # check the answer key against the KB
python scripts/testset_stats.py    # counts by split / category / behaviour + audio minutes
python scripts/build_audio.py      # (re)build audio; existing clips are skipped, so it's free
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
