# data/testset — Test set (Module 3)

`sentences.json` holds 142 short phone-call / voice-note lines with ground truth (the "answer key"):
which KB entities each line mentions, what Pehchaan should do (`correct` / `keep` / `resolve` / `clarify`),
and the expected action (`call` / `book` / `remind` / `message` / `none`).

| category | what it tests | expected |
|---|---|---|
| `in_kb` | names that ARE in the KB | correct them |
| `out_of_kb` | real-sounding names NOT in the KB | keep, link nothing |
| `control` | no names (incl. "cook", "lucky", "sunny") | keep |
| `ambiguous` | near-identical pairs (Harshit / Harshil) | resolve by context, or clarify |
| `context_mismatch` | name matches, context doesn't (Raju Hotel, unknown caller "Raju") | clarify or keep |
| `reference` | personal references ("my doctor", "Amma", "the usual pharmacy") | resolve, or clarify |
| `unfamiliar_near_match` | a name one sound away from a contact, but not a contact ("Rohan" vs "Rohit") | keep (clarify also acceptable) |
| `stale_default` | a clue beats the default ("my doctor about my eye drops" -> eye specialist) | resolve |

`split`: **dev** (45) may be looked at while tuning; **test** (97) is held out for final numbers only.

Audio (built by `scripts/build_audio.py` with OpenAI TTS):
- `audio/clean/{id}.wav`: 24 kHz, as produced by text-to-speech
- `audio/phone/{id}.wav`: 8 kHz, 300-3400 Hz band-pass, light noise ("phone quality")
- `manifest.json`: one row per clip with id, split, category, direction, text, voice, speed, both paths and duration

Validate with:  `python -m app.testset.validate`   Stats:  `python scripts/testset_stats.py`
