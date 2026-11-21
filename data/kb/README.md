# data/kb — Knowledge base

The people, places and businesses Pehchaan matches mis-heard names against (built in Module 2).

- `contacts.json`: fictional personal contacts (`person_XXX`), each with a fake phone number `+91-90000-0XXXX`
- `places.json`: real public place names (`place_XXX`), mostly Hyderabad localities
- `businesses.json`: fictional local businesses (`business_XXX`); each `area` must be a name from `places.json`

The files are loaded and validated by `app/kb/loader.py`. After editing them, run `pytest` and
`python scripts/kb_stats.py` to confirm the data still follows the rules.

Personal-reference fields (vision upgrade):
- people: `roles` (e.g. `["doctor", "dentist"]`), `is_primary_for` (the user's default for a role),
  `family_label` (Amma, Nanna, Akka, Anna, Bhaiya, ...), `last_interaction` (fake ISO date)
- businesses: `is_usual` + `usual_for` (e.g. the usual `pharmacy`, `groceries`, `salon`)
- `preferences.json`: learned answers (`phrase_pattern`, `entity_id`, `created_at`); starts empty, filled in Module 9

## Contact books (Module 9)
`books/A.json` and `books/B.json` are small **overlays** on the base KB, not copies: `remove` drops entities and
`update` changes fields (a `null` value deletes a field). Book A keeps one doctor; book B keeps two doctors and has no
default doctor. `resolve(..., book="B")` (or `with use_book("B"):`) makes every lookup use that book. Learned answers
for a demo book are saved in `books/preferences_<book>.json` (git-ignored runtime state). Evaluation always uses the
`default` book, which is the base KB exactly as it is.
