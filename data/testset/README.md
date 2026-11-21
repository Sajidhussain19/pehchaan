# data/testset — Test set (Module 3)

`sentences.json` holds 113 short phone-call / voice-note lines with ground truth (the "answer key"):
which KB entities each line mentions, what Pehchaan should do (`correct` / `keep` / `resolve` / `clarify`),
and the expected action (`call` / `book` / `remind` / `message` / `none`).

| category | what it tests | expected |
|---|---|---|
| `in_kb` | names that ARE in the KB | correct them |
| `out_of_kb` | real-sounding names NOT in the KB | keep, link nothing |
| `control` | no names (incl. "cook", "lucky", "sunny") | keep |
| `ambiguous` | near-identical pairs (Harshit / Harshil) | resolve by context, or clarify |
| `context_mismatch` | name matches, context doesn't (Raju Hotel, unknown caller "Raju") | clarify or keep |

`split`: **dev** (36) may be looked at while tuning; **test** (77) is held out for final numbers only.

Audio (built by `scripts/build_audio.py` with OpenAI TTS):
- `audio/clean/{id}.wav`: 24 kHz, as produced by text-to-speech
- `audio/phone/{id}.wav`: 8 kHz, 300-3400 Hz band-pass, light noise ("phone quality")
- `manifest.json`: one row per clip with id, split, category, direction, text, voice, speed, both paths and duration

Validate with:  `python -m app.testset.validate`   Stats:  `python scripts/testset_stats.py`
