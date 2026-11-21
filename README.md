# Pehchaan

**AI assistants hear words. Pehchaan understands who you mean.**

> No speech model can know *your* contacts, so personal context has to live outside the model.
> Pehchaan is "the personal ear" that sits after speech-to-text. It gets Indian names right and works out who
> "my doctor" or "Amma" is, so voice assistants take the right action.

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

After speech-to-text, Pehchaan finds name/place spans and personal references in the transcript.
It matches them against your knowledge base (your contacts + Indian places + local businesses) with simple
phonetic + fuzzy matching and a confidence score. An LLM is used only when it's unsure:
**high confidence -> resolve, unsure -> LLM check or ask, unknown -> keep and flag.**
It never hides what it heard: every result shows *heard -> resolved -> confidence -> reason*.
The one real action is **Remind**: a stored reminder with the person, time and place, plus heard vs resolved.

## The 4 levels

| Level | Example | Pehchaan's answer |
|---|---|---|
| 1. Misheard names | "call cook at Polly clinic" | **Kukatpally** |
| 2. Personal references | "call my doctor", "remind me to call Amma", "the usual pharmacy" | the exact contact or business |
| 3. Ambiguity | "call Harshit" (Harshit or Harshil?), "ask my colleague" (19 colleagues) | use clues, otherwise **ask once** |
| 4. Learning | the user picks "Always use Harshil for 'my colleague'" | remembered (only with that consent); "Use Harshil this time" changes nothing |

**Resolution rule:** first a clue in the sentence ("tooth" -> the dentist), then the user's default
("my doctor" -> the family doctor), and if it's still unclear, ask once and remember the answer.

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
| `contacts.json`   | personal contacts: doctors, family, colleagues, drivers, shopkeepers (with roles, defaults, family labels) | 134 |
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

The "same recordings" every system is compared on live in `data/testset/`: **142 short phone-call and voice-note lines**.
They include incoming calls and outgoing commands, some Hinglish / Tenglish, and **11.6 minutes of audio**.
Each line has ground truth: the KB ids of the names in it, what Pehchaan should do, and the expected action
(call / book / remind / message / none).

**8 categories.** Most of the non-headline ones exist to catch *wrong* corrections, not just count successes:

| Category | Lines | Example | Expected |
|---|---|---|---|
| `in_kb` | 68 | "Call Dr. Venkataramana and ask if he is free this evening." | correct |
| `out_of_kb` | 13 | "Call Tejaswini and ask if she reached Nalgonda." | keep |
| `control` | 13 | "The cook at the polling booth said lunch is ready." | keep |
| `ambiguous` | 11 | "Ask Harshil to send the invoice" / "Call Harshit at 5." | resolve / clarify |
| `context_mismatch` | 8 | "Book a table at Raju Hotel…" / unknown caller: "I'm Raju from the bank" | clarify / keep |
| `reference` | 19 | "Call my doctor, my tooth is paining" / "Order Amma's tablets from the usual pharmacy" / "Ask my colleague to join the call" | resolve / clarify |
| `unfamiliar_near_match` | 6 | "Remind me to call Rohan…" (Rohan is not a contact; Rohit is) / unknown caller "Harshil Mehta" | keep (clarify also OK), never resolve |
| `stale_default` | 4 | "Call my doctor about my eye drops" -> the eye specialist, not the default family doctor | resolve |

**4 expected behaviours:** **correct** (fix a known name), **keep** (leave unknown names and ordinary words alone),
**resolve** (pick the right look-alike contact, or work out who "my doctor" means, using context), **clarify** (ask the user instead of guessing).

**Dev / test split:** 45 **dev** lines may be inspected while tuning. 97 **test** lines are held out and used only
for the final numbers. The split is stratified, so every category appears in both.

**Audio:** every line was spoken by OpenAI text-to-speech (`gpt-4o-mini-tts`, Indian English accent, 8 rotating voices,
4 speeds). Each line comes in two versions:
- `audio/clean/` (24 kHz)
- `audio/phone/`: 8 kHz, 300-3400 Hz band-pass, light noise, i.e. what a phone call actually carries

`manifest.json` lists every clip. The audio (43 MB) is committed so you can listen to it.

**Honest limitation:** this is *synthetic* TTS audio. Real human recordings, with hesitations, background chatter
and strong regional accents, would be harder, so absolute error rates here are optimistic. The comparison between
systems is still fair, because every system hears exactly the same audio.

### Real speakers (over-correction check)

`data/realspeech/` holds a small sample (40 clips from 40 speakers, 4.8 min, 9.3 MB) of **real Indian-accented English**
from **Svarah** by AI4Bharat (IIT Madras): https://huggingface.co/datasets/ai4bharat/Svarah.
The speakers' first languages range from Kannada and Telugu to Bodo, Dogri and Kashmiri. The HF copy has no speaker-id
column, so `speaker_id` is the speaker's profile (language, state, district, gender, age, education, job).
These clips rarely contain our KB names, so the expected behaviour is "keep". They test whether Pehchaan
makes real transcripts *worse*.

- **Licence:** [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). We use unmodified clips and their
  reference transcripts for evaluation only.
- **Attribution:** Tahir Javed et al., *"Svarah: Evaluating English ASR Systems on Indian Accents"*,
  INTERSPEECH 2023 (arXiv:2305.15760).
- **Access:** the dataset is *gated* on Hugging Face. Accept its conditions with your HF account, put a read token
  in `.env` as `HF_TOKEN`, then run `python scripts/fetch_real_speech.py`.

```powershell
python -m app.testset.validate     # check the answer key against the KB
python scripts/testset_stats.py    # counts by split / category / behaviour + audio minutes
python scripts/build_audio.py      # (re)build audio; existing clips are skipped, so it's free
```

## How it works
*Coming in later modules (6-9).*

## Baselines (Module 4)

Every clip is transcribed by OpenAI speech-to-text, **`gpt-4o-mini-transcribe`** by default
(`gpt-4o-transcribe` and `whisper-1` are also supported):
- **(a) plain:** the audio only, with no prompt
- **(b) name hints:** the same audio plus a prompt listing the user's names
  ("Names and places that may appear: Dr. Venkataramana, Kukatpally, …")
  - Contacts come first, then Hyderabad places, businesses and other places.
  - The whole KB (340 names, about 1,300 tokens) fits in gpt-4o-mini-transcribe's prompt, so (b) is as strong as we can fairly make it.
  - With `whisper-1` (a 224-token prompt) only 54 names fit.

| Results file | KB names missed (exact match) |
|---|---|
| plain, clean audio | 47 / 106 (44%) |
| plain, phone audio | 55 / 106 (52%) |
| hints, clean audio | 25 / 106 (24%) |
| hints, phone audio | 25 / 106 (24%) |

On **real speech** (40 Svarah clips, no KB names): rough WER is plain 9.5% vs hints 6.6%, and the hints inserted
**no** KB names into real transcripts.

Examples from plain speech-to-text:
- "Thirumalai Selvan" -> "The roomer Life Selvan"
- "Anjani" -> "Aunt Johnny"
- "Abids" -> "a bit"
- "Kakatiya Kitchen" -> "Cockatiel Kitchen"

Hindi/Telugu code-mixed lines often come back in **Devanagari or Telugu script**, so a Latin-script name can't be found at all.

*These are rough exact-match counts. The real metrics come in Module 5.* **Honest note:** hints already halve the misses.
The fair opponent is therefore not (a) but (b) and, above all, **(c) the strong LLM baseline**. (c) gets the same
contacts and roles and can ask, and it is built next, in Module 5. Hints also can't decide *which* "doctor" you meant.

```powershell
python scripts/run_baseline.py --limit 3     # cheap check (3 clips per combination)
python scripts/run_baseline.py               # everything; cached clips are skipped (free)
python scripts/show_errors.py                # missed names + the 5 most dramatic mistakes
```
Results are in `data/results/baseline_{plain|hints}_{clean|phone|real}_{model}.json`.

## Evaluation plan
Four systems run on the same recordings, and results are reported on the **held-out test split**:
- (a) plain speech-to-text
- (b) speech-to-text with name hints in the prompt
- (c) a **strong LLM baseline**: one GPT-4o-mini call with the transcript plus the same contacts, roles, defaults,
  places and businesses, allowed to ask
- (d) Pehchaan

We report **per-case wins / ties / losses vs (c)**, not just averages. Each metric is reported separately:
- action-target accuracy
- wrong-target rate
- unnecessary-question rate
- over-correction rate
- missed-clarification rate
- reference-resolution accuracy
- latency and cost per call
- the share of cases resolved with no LLM call

*Results come in Module 5.*

## Demo
*Coming in Module 10.*

## Deployment (AWS EC2)
*Coming in Module 10.*
