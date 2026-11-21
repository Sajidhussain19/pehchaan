"""
app/store/preferences.py — saves and resets learned answers ("Always use X for 'my doctor'"), per contact book.

WHAT: save(book, phrase, entity_id) appends a Preference to that book's preferences file;
      reset(book) empties it. Reading is done by app/kb/loader.load_preferences(), which the pipeline's
      first node (preferences) calls, so a saved answer is used on the very next request.
WHY:  Level 4 of the vision: learning, but ONLY with consent. Only the "always" button calls save();
      "this time" never writes anything. Each book has its own file because "my doctor" can mean a
      different person for a different user.
"""

import json
import threading
from datetime import datetime

from app.kb.loader import get_by_id, preferences_path, use_book
from app.kb.models import Preference

_LOCK = threading.Lock()  # two requests saving at once must not overwrite each other's line


def save(book: str, phrase: str, entity_id: str) -> Preference:
    """Remember that, in this book, `phrase` means `entity_id`. A later answer for the same phrase wins."""
    with use_book(book):
        if get_by_id(entity_id) is None:
            raise KeyError(f"{entity_id} is not in contact book {book!r}")
        path = preferences_path(book)
    pref = Preference(phrase_pattern=phrase, entity_id=entity_id, created_at=datetime.now())
    with _LOCK:
        rows = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        rows.append(pref.model_dump(mode="json"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return pref


def reset(book: str) -> int:
    """Forget everything learned for this book (for repeated demos). Returns how many answers were removed."""
    with use_book(book):
        path = preferences_path(book)
    with _LOCK:
        n = len(json.loads(path.read_text(encoding="utf-8"))) if path.exists() else 0
        if path.exists():
            path.write_text("[]\n", encoding="utf-8")
    return n
