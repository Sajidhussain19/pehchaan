# Pehchaan

## Judge summary

- Indian names and phrases like “my doctor” can send a voice reminder to the wrong person.
- Pehchaan uses personal contacts and sentence clues to pick the recipient, asks when needed and stores the reminder.
- On the same 90 fresh held-out recordings, wrong-target actions fell from 10 with Strong AI to 2 with Pehchaan. Pehchaan also asked 4 unnecessary questions versus 0.
- [Try the live five-step doctor demo](https://d1rcvr2z1hg6u0.cloudfront.net).
- After installing the requirements on Python 3.12, verify in about 30 seconds with `python scripts/e2e_check.py`. [Evaluator guide](AGENTS.md)

**AI assistants hear words. Pehchaan understands who you mean.**

> No speech model can know *your* contacts, so personal context has to live outside the model.
> Pehchaan is "the personal ear" that sits after speech-to-text. It gets Indian names right and works out who
> "my doctor" or "Amma" is, so voice assistants take the right action.

*Built solo for Builders 2026 by OpenAI x Equal AI, Hyderabad. Track: Build Challenging — Voice AI for India.*

**Deck, cheat sheet, video:** [Deliverables](#deliverables)

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

Pehchaan is **a hybrid AI system: speech AI on every voice request (demo clips replay their saved transcripts), LLM reasoning only for hard cases.** Most requests are decided on the fast path (sound matching + your personal context, no LLM call needed).

## Results (held-out test split, run once)

Measured on the **held-out test split** (97 sentences × clean + phone audio, plus 26 real-speaker clips = 220 clips),
run **once** after the decision logic was frozen (git tag `final-eval-v1`; report: `data/results/report_test_FINAL.md`).
Baseline (c) is one GPT-4o-mini call that gets the same transcript and the user's whole personal context.

| | (c) strong LLM baseline | **Pehchaan** |
|---|---|---|
| **wrong-target rate** (acted on the wrong person/place) | 24/220 = 11% | **11/220 = 5%** |
| **missed clarifications** (guessed when it should ask) | 14/14 = 100% | **1/14 = 7%** |
| reference resolution ("my doctor", "Amma", "the usual pharmacy") | 19/32 = 59% | **32/32 = 100%** |
| exact action target | 74/118 = 63% | **96/118 = 81%** |
| behaviour (correct / keep / resolve / ask) | 162/220 = 74% | **182/220 = 83%** |
| entity accuracy | 109/148 = 74% | **118/148 = 80%** |
| WER (supporting) | 292/2392 = 12% | **265/2392 = 11%** |
| over-correction (changed a name that should stay) | **3/70 = 4%** | 11/70 = 16% |
| unnecessary questions | **0/198 = 0%** | 15/198 = 8% |
| decided with **no LLM call** | 0/220 = 0% | **191/220 = 87%** |
| latency per decision (median / mean) | 1502 / 1549 ms | **11 / 298 ms** |
| cost per decision (mean) | $0.00097 | **$0.000012** |

**Clip by clip, Pehchaan vs (c): 49 wins, 149 ties, 22 losses.** Pehchaan halves wrong actions and asks when it
should; its weak spots are **over-correction** (e.g. Telugu "ee roju", *today*, turned into "Dr. Raju") and asking
when a business name contains a contact's first name ("Lakshmi Ganapathi Tiffins"). Both are reported as they are:
nothing was tuned after this run. On dev we had seen 0/34 over-corrections; the test split showed that was optimistic.
Those two weak spots are what **v2** fixes, proven on a second, fresh held-out set (see "v2 changes" below).

## v2 changes (over-correction fixes, proven on a fresh held-out set)

The headline above (v1, tags `final-eval-v1` / `v1.1`) is **never overwritten**. v2 fixes the two weak spots that
held-out run exposed, and it is proven on **test-2**: a brand-new held-out set.

**How it was proven (in this order, each step tagged in git and pushed before the next):**
1. **`test2-frozen`:** 45 new sentences (s164–s208) were written, with clean + phone audio and plain transcripts,
   **before any v2 code existed**. They don't paraphrase any dev/test sentence (max similarity 0.74; four closer
   ones were rewritten). They are weighted toward v1's general weak spots (code-mixed sentences with no names,
   businesses containing a contact's first name, unknown callers with a contact's surname, real names not in the
   KB), plus normal cases so improvements can't hide regressions.
2. **`pehchaan-v2`:** the fixes, tuned on **dev only** (2 rounds). On dev v2 kept wrong targets at 0/146 and
   missed clarifications at 1/16.
3. **test-2, run once** behind `--final-test2` (logged in `data/results/test_runs.log`): strong AI (c), v1 (the
   exact code of tag `final-eval-v1.1`, run from a git worktree) and v2. Nothing was tuned afterwards.
   Report: `data/results/report_test2_FINAL.md`.

**What changed (general rules, not per-clip patches):**
| Fix | Why (v1's failure, in general) |
|---|---|
| Everyday-word guard: a phrase made only of everyday Telugu/Hindi/Tamil/Kannada/Malayalam words (`data/lexicon/indian_everyday_words.txt`, romanised + native script) is never turned into a name, unless it is in a strong name position ("call …", "Dr. …", "to <place>") and matches ≥ 0.95 | "ee roju" (*today*) became "Dr. Raju" |
| Longest match first: a multi-word span that confidently matches a multi-word KB name wins over a first name inside it (and must not start or end with an ordinary word) | "Lakshmi Ganapathi Tiffins" → "which Lakshmi?" |
| Caller evidence: a known caller introducing themself ("Srinivas Gowd here") is the caller | asked "which Srinivas?" on the caller's own number |
| Unknown-caller surname: an unknown number sharing only a surname is never linked | "Harshal Mehta" → Dr. Alok Mehta |
| LLM fallback answers "keep" unless the sentence clearly refers to a candidate | "Gokul" → Mangaluru |

**test-2 results (90 clips: 45 × clean + phone; raw counts):**
| | (c) strong LLM baseline | Pehchaan v1 | **Pehchaan v2** |
|---|---|---|---|
| wrong-target rate | 10/90 = 11% | 9/90 = 10% | **2/90 = 2%** |
| missed clarifications | 8/8 = 100% | 2/8 = 25% | **2/8 = 25%** |
| over-correction | 3/36 = 8% | 5/36 = 14% | **2/36 = 6%** |
| unnecessary questions | **0/78 = 0%** | 5/78 = 6% | 4/78 = 5% (still worse than (c)) |
| reference resolution | 10/14 = 71% | 11/14 = 79% | 11/14 = 79% |
| exact action target | 34/40 = 85% | 29/40 = 72% | **36/40 = 90%** |
| entity accuracy | 47/52 = 90% | 45/52 = 87% | **49/52 = 94%** |
| decided with no LLM | 0/90 | 83/90 = 92% | 84/90 = 93% |
| latency median / mean | 1670 / 1728 ms | 13 / 250 ms | 11 / 188 ms |

Clip by clip: **v2 vs (c): 25 wins, 62 ties, 3 losses. v2 vs v1: 11 wins, 79 ties, 0 losses.**

**v2 on the ORIGINAL test set: already seen, NOT a clean held-out result** (v2's fixes were designed after looking
at v1's losses there; `data/results/report_test_v2_SEEN.md`): wrong targets 8/220 (v1 11), over-correction 4/70
(v1 11, (c) 3), unnecessary questions 5/198 (v1 15, (c) 0), entity accuracy 130/148 (v1 118).

**Disclosed:** the first v1 run on test-2 was invalid. The temporary worktree had no `.env`, so v1's LLM fallback
could not run and "kept" those spans. It was discarded **before any scoring**, the runner was fixed (it now passes
the key to the child process and refuses to save a run with LLM failures), and v1 was run again. The demo now runs
v2. The clip list starts with the original test set (seen before v2), followed by dev clip s101 (used for tuning), the held-out test-2 examples (`data/results/demo_candidates.md`), and the remaining dev clips.

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

Use Python 3.12. The local demo, saved clips and evaluator check work without an OpenAI key.

```powershell
# 1. Create and activate a virtual environment
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Verify the judge journeys (expected: ALL PASSED)
python scripts/e2e_check.py

# 4. Run the server, then open http://127.0.0.1:8000
uvicorn app.main:app --reload

# 5. Run the tests
pytest -q
```

On macOS/Linux, create the environment with `python3.12 -m venv venv` and activate with `source venv/bin/activate`.
For live transcription and live AI comparison, optionally configure `OPENAI_API_KEY` as described in [AGENTS.md](AGENTS.md#3-environment-variables).

## Project layout

```
app/            FastAPI app and all project code
  api/          HTTP endpoints (routes.py), the flow (flow.py), safe audio handling (audio.py)
  store/        SQLite reminders + pending questions, learned preferences per contact book
  decide/       the LangGraph decision pipeline        match/  spans + phonetic matching
data/kb/        knowledge base (contacts, places, businesses)
data/kb/books/  demo contact books A and B (small overlays on the base KB)
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

The "same recordings" every system is compared on live in `data/testset/`: **163 short phone-call and voice-note lines**.
They include incoming calls and outgoing commands, some Hinglish / Tenglish, and **13.1 minutes of audio**.
Each line has ground truth: the KB ids of the names in it, what Pehchaan should do, and the expected action
(call / book / remind / message / none).

**8 categories.** Most of the non-headline ones exist to catch *wrong* corrections, not just count successes:

| Category | Lines | Example | Expected |
|---|---|---|---|
| `in_kb` | 79 | "Call Dr. Venkataramana and ask if he is free this evening." | correct |
| `out_of_kb` | 13 | "Call Tejaswini and ask if she reached Nalgonda." | keep |
| `control` | 13 | "The cook at the polling booth said lunch is ready." | keep |
| `ambiguous` | 14 | "Ask Harshil to send the invoice" / "Call Harshit at 5." | resolve / clarify |
| `context_mismatch` | 10 | "Book a table at Raju Hotel…" / unknown caller: "I'm Raju from the bank" | clarify / keep |
| `reference` | 23 | "Call my doctor, my tooth is paining" / "Order Amma's tablets from the usual pharmacy" / "Ask my colleague to join the call" | resolve / clarify |
| `unfamiliar_near_match` | 6 | "Remind me to call Rohan…" (Rohan is not a contact; Rohit is) / unknown caller "Harshil Mehta" | keep (clarify also OK), never resolve |
| `stale_default` | 5 | "Call my doctor about my eye drops" -> the eye specialist, not the default family doctor | resolve |

**4 expected behaviours:** **correct** (fix a known name), **keep** (leave unknown names and ordinary words alone),
**resolve** (pick the right look-alike contact, or work out who "my doctor" means, using context), **clarify** (ask the user instead of guessing).

**Dev / test split:** 66 **dev** lines (incl. 21 hard dev-only lines added before Module 8) may be inspected while tuning. 97 **test** lines are held out and used only
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
- **Not in this repo:** the audio files are not redistributed here (`data/realspeech/audio/` is git-ignored).
  The manifest, attribution, saved transcripts and all results are included, so every reported number can be
  re-scored without the audio; fetch the audio as above to re-transcribe or to play the real clips in the demo.

```powershell
python -m app.testset.validate     # check the answer key against the KB
python scripts/testset_stats.py    # counts by split / category / behaviour + audio minutes
python scripts/build_audio.py      # (re)build audio; existing clips are skipped, so it's free
```

## How it works

**Step 1: candidate spans + phonetic matching (Modules 6+7, no LLM, ~8 ms per sentence).**
- **Spans:** every 1-4 word chunk of the transcript is compared by **sound** to every way a KB entity can be written.
  Speech-to-text splits names into English words: "Aunt Johnny" (Anjani), "a bit" (Abids), "the roomer life" (Thirumalai).
- **Sound keys:** Indian-English rules (th→t, aa→a, w→v, sh→s…) plus Double Metaphone ("cook at polly" and
  "Kukatpally" both become `KKTPL`).
- **Indian scripts:** code-mixed lines that STT wrote in Devanagari or Telugu are transliterated first.
- **Personal references** ("my doctor", "Amma", "the usual pharmacy") are found by phrase rules, with every fitting entity attached.
- **Protection:** common-English and length penalties keep "lucky", "the cook" and "said" away from contacts.
- **Output:** each span with its top 3 candidates, scores, the margin between the top two, and the reasons.

```powershell
python scripts/inspect_candidates.py "Call Aunt Johnny and ask if tuition is on"
python scripts/eval_candidates.py            # dev split: recall@1/@3, false alarms, speed
```

**Step 2: decisions (Module 8, a LangGraph pipeline, one node per step).**

```
preferences → candidates → references → context_check → route ─(unsure?)→ llm_fallback → action → assemble
```
- **References:** a clue in the sentence beats the default ("my doctor, my **tooth**…" → the dentist), the default beats
  asking ("my doctor" → the family doctor), and otherwise it asks ("my colleague" → 19 people).
- **Context:** an unknown caller saying "I'm Raju" is not your Dr. Raju; "book a **table** at Raju Hotel" can't silently become a doctor.
- **Routing:** clear winners resolve; close calls use clue words, otherwise **ask** ("Call Harshit at 5": Harshit or Harshil?);
  a real name that isn't a contact ("Sravanthi") is never silently "fixed" into Sravani.
- **The LLM** (gpt-4o-mini) is called only for leftovers, with just the sentence and the top-3 candidates.
- **Output:** the same `Decision` as baseline (c), with every entity shown as *heard → resolved → confidence → reason*,
  plus a Remind action (who, where, "HH:MM").

**Results:** see [Results (held-out test split, run once)](#results-held-out-test-split-run-once). Dev-split numbers (which we tuned on) are in `LEARNING.md` and `data/results/report_dev_all.md`.

```powershell
python scripts/run_pehchaan.py            # dev split, clean + phone + real (LLM answers cached)
python scripts/evaluate.py                # dev report: (a), (b), (c), Pehchaan + win/tie/loss
```

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

## Evaluation (Module 5)

Four systems are scored on the **same clips** with **the same rules**:
- **(a)** plain speech-to-text
- **(b)** speech-to-text + name hints
- **(c)** the **strong LLM baseline**: one GPT-4o-mini call given the transcript, the call context and the user's
  *whole* personal context (contacts with roles, defaults and family labels; businesses with "usual for"; places).
  It is told the same rules Pehchaan follows (clue -> default -> ask; never invent; keep unknown names), and a strict
  output schema means it can only answer with real KB ids.
- **(d)** Pehchaan, from Module 8 on

(c) and Pehchaan output the same `Decision` format: heard -> resolved -> confidence -> reason, a behaviour, and a Remind action.

**Metrics, in plain words.** Each one is reported **separately, with raw counts** (e.g. `7/12 = 58%`):

| Metric | Question it answers |
|---|---|
| entity accuracy | Did the KB names end up spelled right in the transcript? |
| WER | How many words of the whole sentence are wrong? |
| over-correction rate | When nothing should change (unknown names, ordinary words, real speech), did a KB name appear anyway? |
| behaviour accuracy | Did it correct / keep / resolve / ask when it should? |
| exact action-target accuracy | Is the reminder about the right person/business, at the right place? (time is scored separately) |
| **wrong-target rate** | Did it act on the WRONG entity, or use an id that doesn't exist? (the worst error) |
| unnecessary-question rate | Did it ask when the answer was clear? |
| missed-clarification rate | Did it guess when it should have asked? |
| reference-resolution accuracy | Did "my doctor", "Amma" and "the usual pharmacy" resolve to the right entity? |
| no-LLM rate, latency, cost | How often no LLM was needed, how long a call took, and what it cost |

**Why separate scores?** One blended number would let a system that is good on average hide the dangerous mistakes,
like calling the wrong person. And raw counts show how much evidence each percentage rests on.

**Held-out rule.** Everything is tuned and inspected on the **dev** split only. Scoring the **test** split needs
`--final`, prints a warning, and is logged in `data/results/test_runs.log`, so every look at the test set is on record.

**What the evaluation showed.** The strong baseline fixes many spellings, but it **almost never asks when it should**: it guesses between Rohit and Rohith, maps "Venkataramana Restaurant" to a dental clinic, and sends "my doctor about the tooth filling" to the family doctor. Final held-out numbers for all systems: [Results](#results-held-out-test-split-run-once) and `data/results/report_test_FINAL.md`.

```powershell
python scripts/run_llm_baseline.py --limit 3     # baseline (c), dev split, cached
python scripts/evaluate.py --split dev --systems c v1 v2 --compare v2 c --out dev_check
```

### Test-set errata (fixed before the final run)
One ground-truth label was wrong, and we fixed it **before** the single held-out run, without looking at any test
results. We did **not** edit the knowledge base to fit the label; we re-derived the label from the KB as it is, using
our documented rule (clue -> default -> ask).

| Clip | Sentence | Old label | New label | Why |
|---|---|---|---|---|
| s142 (test) | "Remind me to ask my accountant whether the GST papers are ready." | category `stale_default`; "my accountant" -> **Meenakshi Sundaram** (person_030) by `clue` | category `reference`; "my accountant" -> **Sunita Agarwal** (person_058) by `primary` (the default); behaviour `resolve`, Remind target person_058 | Nothing in the KB links "GST" to any accountant (Meenakshi Sundaram's notes are empty), so there is no clue. The rule then says: use the default, and Sunita Agarwal is the contact marked as default accountant. The old label could not be derived from the data by any system. The sentence moves category because "stale_default" means "a clue beats the default", which no longer applies. The text and audio are unchanged. |

### Decision-logic freeze
From the final held-out run on, **Pehchaan's decision logic is frozen**: `app/match/`, `app/decide/`, `data/lexicon/`
and the base KB files. Their fingerprints (SHA-256) are in `data/results/frozen_logic.json`, and `tests/test_freeze.py`
fails if any of them changes. Any later change needs explicit approval, a repeated final run (`--final`), and a note here.

### Changes after final evaluation
| Tag | Change | Approved | Effect on the held-out numbers |
|---|---|---|---|
| `final-eval-v1.1` | **A clue in the sentence beats a saved preference** (rule: clue -> saved preference -> default -> ask). Before, "Always use Dr. Subramanian for 'my doctor'" also sent "call my doctor about my **fever**" to the dentist; now the clue "fever" picks the GP. Only for references ("my doctor"); learned answers for plain names are unchanged. | yes, by the developer (Module 10) | Re-ran the final evaluation once with `--final`: **all 366 decisions (dev + test, every audio) identical**, every scored metric identical (evaluation uses no saved preferences). Only latency was re-measured (Pehchaan mean 298 -> 170 ms, median 10.9 -> 9.4 ms; cached LLM answers reuse their recorded time). The Results table keeps the first, more conservative latency. |
| `pehchaan-v2` | **v2: over-correction fixes** (everyday-word guard, longest match first, caller evidence, unknown-caller surname, LLM prefers keep). Developer-approved unfreeze. | yes (v2 brief) | The v1 headline is unchanged and still reproducible from `final-eval-v1.1`. v2 is proven on the fresh test-2 set (see "v2 changes"); on the original test set it is reported only as "already seen". |
| (after `pehchaan-v2`) | **AI-failure branch only:** if Pehchaan's LLM step fails (timeout, 5xx, rate limit, no key) it now **asks** with the top candidates ("AI unavailable — asked you instead") instead of keeping the name; with no plausible candidate it keeps it. Also outside the decision logic: a failing strong-AI comparison no longer breaks the response, live speech-to-text failures return a clear 503, and OpenAI calls time out after 20 s. | yes (developer) | **None.** No saved evaluation decision ever took this branch (none contains "LLM unavailable"). Re-running all 146 dev decisions with the new code: **0 differ**. Held-out sets were not re-run. Fingerprint re-recorded. |

*Made just before the freeze (Module 9 plumbing, no logic change):* the KB-derived caches in `app/match` and
`app/decide` became per-contact-book caches, and `resolve()` gained a `book=` argument. Re-running Pehchaan on all
146 dev decisions gave **0 differences** from the Module 8 outputs (latency ignored).

## API

Start the server: `uvicorn app.main:app --reload`, then open http://127.0.0.1:8000/docs for the interactive docs.

| Endpoint | What it does |
|---|---|
| `GET /health` | the server is up |
| `GET /api/books` | contact books (`default`, `A`, `B`) with a one-line description |
| `GET /api/clips` | demo clips from the held-out run first, then dev clips, with audio URLs |
| `GET /audio/{clean\|phone\|real}/{clip_id}.wav` | one clip's audio (ids checked against the manifests; no path traversal) |
| `POST /api/process` | form fields: exactly one of `file` (mic recording: webm/ogg/wav/mp3/m4a, ≤ 5 MB, ≤ 30 s), `clip_id` + `variant`, or `text`; plus `book`, `compare` |
| `POST /api/clarify/{pending_id}` | JSON `{"entity_id": "...", "remember": "this_time" \| "always"}` → creates the reminder; `always` also saves a preference for that book |
| `POST /api/preferences/reset?book=B` | forget what a book learned (repeatable demos) |
| `GET /api/reminders`, `GET /api/reminders/{id}`, `DELETE /api/reminders` | the stored reminders |
| `GET /api/metrics` | the FINAL held-out numbers, (c) vs Pehchaan with raw counts, for the scoreboard |

The browser sends a random UUIDv4 in `X-Visitor-Id`. Reuse it on process, clarify, and reminder requests. Reminders and questions belong to that visitor. Learned preferences are shared per book.

`POST /api/process` runs **speech-to-text → Pehchaan → a stored reminder, or a pending question**. With `compare=true`
it also runs baseline (c) on the same transcript and returns its decision side by side (never stored). The response
has the heard transcript, the corrected transcript with every span marked (heard text, resolved name, role,
confidence, reason, character positions for highlighting), the decision, and timings: `stt_ms`, `pehchaan_ms`,
`baseline_ms`, `total_ms`, plus `used_llm` and `cost_usd` (speech-to-text + Pehchaan).

```powershell
$visitor = [guid]::NewGuid().ToString()
curl.exe -X POST http://127.0.0.1:8000/api/process -H "X-Visitor-Id: $visitor" -F "text=Remind me to call my doctor at six." -F book=B
curl.exe -X POST http://127.0.0.1:8000/api/process -H "X-Visitor-Id: $visitor" -F clip_id=s140 -F variant=phone -F compare=true
```

Reminders live in SQLite (`data/app.db`, Python's built-in `sqlite3`, no ORM). Each one stores the person, role,
place, `HH:MM` time (or none if the time was ambiguous), heard vs corrected transcript, every entity's
heard → resolved → confidence → reason, and how it was decided: `auto`, `clarified_this_time`, `clarified_always`
or `preference`.

## Demo flow

**Two contact books, one sentence.** "Remind me to call my doctor at six." means different things for different users:

| Book | Contacts | Result |
|---|---|---|
| A | one doctor (Dr. Venkataramana, family doctor) | reminder for Dr. Venkataramana, no question |
| B | two doctors (general physician + dentist), no default | **asks**: Dr. Venkataramana or Dr. Subramanian? |

In book B: **"Use Dr. Subramanian this time"** creates the reminder and learns nothing (it asks again next time).
**"Always use Dr. Subramanian for 'my doctor'"** saves a preference for book B only; the next time, the same sentence
resolves automatically (`resolution = preference`). A clue still works without learning: "my doctor, my **tooth**
is paining" → the dentist.

```powershell
python scripts/demo_flow.py              # the whole story, step by step ($0; temporary database)
python scripts/demo_flow.py --compare    # + baseline (c) on the book-B sentence (one GPT-4o-mini call)
```

The held-out clips where Pehchaan and (c) diverge, plus one honest Pehchaan failure, are in
`data/results/demo_candidates.md`.

## Run the demo

```powershell
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --port 8000
```

Open **http://localhost:8000** in Chrome or Edge. The page (`web/`, plain HTML + CSS + JavaScript, no build step) has:

- **Header:**
  - the contact book (*Full contacts*, *A: one doctor*, *B: two doctors (starts with no default)*)
  - "Compare with strong AI" (on by default)
  - the **Scoreboard** tab
  - **▶ Start the 5-step doctor demo**
- **Left, three ways in:**
  - clip previews from the labelled groups above, with Play, Run and a Clean/Phone switch. Replays display the saved action without creating a reminder or pending question
  - **Tap to record** (live mic, at most 15 s)
  - a text box
- **Middle:**
  - *Strong AI* vs *Pehchaan*: the transcript with names highlighted, *heard → resolved*, a confidence chip or a count of close matches, the reason (click), the action, and the source and timing scope for each decision
  - for test-set clips, a verdict in words (✓ Correct / ✗ Wrong target / ✗ Should have asked …) from the same scoring code as the evaluation
  - when Pehchaan asks, candidate cards with **Use this time** / **Always use for '…'**
- **Right:** the real saved reminders (click to open), and **Reset demo**.

The microphone works on **localhost** or **https://** only (a browser rule). The public demo runs behind CloudFront
for HTTPS: see [DEPLOY.md](DEPLOY.md). A 2-minute backup recording script is in [DEMO_SCRIPT.md](DEMO_SCRIPT.md).

**Protection for a public link:**
- `POST /api/process` is limited to 20 requests per 10 minutes per visitor.
- OpenAI spending has an approximate $2/day cap (tracked in SQLite).
- Optional `DEMO_KEY` password.
- Requests from other websites are refused.

The OpenAI key never reaches the browser.

## Live demo link

**https://d1rcvr2z1hg6u0.cloudfront.net** (see [DEPLOY.md](DEPLOY.md): EC2 t3.small in us-west-2
behind CloudFront). If it is down, run it locally as above; the mic works on localhost.

## Deliverables

| File | What it is |
|---|---|
| [deliverables/Pehchaan_Slides.pdf](deliverables/Pehchaan_Slides.pdf) | Pitch deck (7 slides: 5 main + 2 appendix) |
| [deliverables/Pehchaan_Slides.pptx](deliverables/Pehchaan_Slides.pptx) | The same deck as PowerPoint, with speaker notes |
| [deliverables/Pehchaan_Cheatsheet.pdf](deliverables/Pehchaan_Cheatsheet.pdf) | One-page cheat sheet |
| [deliverables/Pehchaan_demo_full.mp4](deliverables/Pehchaan_demo_full.mp4) | Narrated demo video, 4:55, 1080p ([VIDEO.md](VIDEO.md)) |

**To run, test and evaluate it yourself (or with an AI agent): [AGENTS.md](AGENTS.md).**

## Deployment (AWS)

Docker image (`Dockerfile`, non-root, port 8000; the key is passed at run time and is never in the image) on EC2,
with CloudFront in front for HTTPS. Step-by-step: [DEPLOY.md](DEPLOY.md). Update after a push: `./deploy/update.sh`
on the server.
