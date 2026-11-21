"""
app/kb/loader.py — loads, validates and serves the knowledge base.

WHAT: Reads data/kb/contacts.json, places.json and businesses.json, turns every row into an
      `Entity` (Pydantic validates each one), runs checks across the whole KB, and offers
      simple lookups: by type, by id, and "every surface form -> entity ids".
WHY:  Every later module (matching, the LangGraph pipeline, the API) needs the KB. One loader
      means one place where the data is read and checked. Caching means the JSON is read from
      disk only once, even if the API asks for the KB on every request.

Usage:
    from app.kb.loader import load_kb, get_by_id, all_surface_forms
    kb = load_kb()
"""

import json
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from app.config import PROJECT_ROOT
from app.kb.models import Entity

KB_DIR = PROJECT_ROOT / "data" / "kb"
KB_FILES = ("contacts.json", "places.json", "businesses.json")


class KBValidationError(ValueError):
    """Raised when the knowledge base data breaks one of our rules."""


def _normalise(text: str) -> str:
    """Lower-case and squash spaces, so 'Dr.  Mehta' and 'dr. mehta' compare as equal."""
    return " ".join(text.lower().split())


def validate_entities(entities: list[Entity]) -> None:
    """Checks that look at the whole KB at once (Pydantic only sees one entity at a time).

    Raises KBValidationError listing every problem found, so you can fix them all in one go.
    It is a separate function so tests can feed it deliberately broken data.
    """
    problems: list[str] = []

    # 1. Unique ids: get_by_id() would silently return the wrong entity if two shared an id.
    seen_ids: set[str] = set()
    for e in entities:
        if e.id in seen_ids:
            problems.append(f"duplicate id: {e.id}")
        seen_ids.add(e.id)

    # 2. No empty names. Pydantic already blocks this; we re-check here as a safety net
    #    in case someone builds Entity objects without validation.
    for e in entities:
        if not e.name.strip():
            problems.append(f"empty name: {e.id}")

    # 3. No duplicate canonical names. Two entities with the same correct spelling would make
    #    a correction ambiguous by design.
    canonical: dict[str, str] = {}
    for e in entities:
        key = _normalise(e.name)
        if key in canonical:
            problems.append(f"duplicate canonical name {e.name!r}: {canonical[key]} and {e.id}")
        canonical[key] = e.id

    # 4. An alias must never equal ANOTHER entity's canonical name.
    #    Example: if "Sreenivas Goud" were also an alias of "Srinivas Reddy", hearing
    #    "Sreenivas Goud" could map to the wrong person. Near-duplicates must stay separate.
    for e in entities:
        for alias in e.aliases:
            owner = canonical.get(_normalise(alias))
            if owner is not None and owner != e.id:
                problems.append(f"alias {alias!r} of {e.id} is the canonical name of {owner}")

    # 5. Every business area must be a real place in the KB, so "book at <business>"
    #    can always be tied to a known location.
    place_names = {_normalise(e.name) for e in entities if e.type == "place"}
    for e in entities:
        if e.type == "business" and _normalise(e.context["area"]) not in place_names:
            problems.append(f"business {e.id} has unknown area {e.context['area']!r}")

    if problems:
        raise KBValidationError("Knowledge base is invalid:\n  - " + "\n  - ".join(problems))


def _read_file(path: Path) -> list[Entity]:
    """Read one JSON file and validate every row as an Entity."""
    rows = json.loads(path.read_text(encoding="utf-8"))
    # model_validate checks each dict against the Entity model and raises a clear
    # error naming the bad field if something is wrong.
    return [Entity.model_validate(row) for row in rows]


@lru_cache(maxsize=1)
def _load_cached() -> tuple[Entity, ...]:
    """Read all KB files once. lru_cache remembers the result, so later calls skip the disk.

    It returns a tuple (which cannot be changed) so that no caller can accidentally
    modify the shared cached copy.
    """
    entities: list[Entity] = []
    for filename in KB_FILES:
        entities.extend(_read_file(KB_DIR / filename))
    validate_entities(entities)
    return tuple(entities)


def load_kb() -> list[Entity]:
    """Return every entity in the KB (contacts, then places, then businesses)."""
    return list(_load_cached())


def get_by_type(entity_type: str) -> list[Entity]:
    """Return all entities of one type: 'person', 'place' or 'business'."""
    return [e for e in _load_cached() if e.type == entity_type]


@lru_cache(maxsize=1)
def _index_by_id() -> dict[str, Entity]:
    # Build the id -> entity dictionary once, so each lookup is instant.
    return {e.id: e for e in _load_cached()}


def get_by_id(entity_id: str) -> Entity | None:
    """Return the entity with this id, or None if there is no such id."""
    return _index_by_id().get(entity_id)


def all_surface_forms() -> dict[str, list[str]]:
    """Map every name and alias (lower-cased) to the ids of the entities that use it.

    The value is a LIST of ids because a short alias can honestly belong to more than one
    entity. That ambiguity is real, and later modules need to see it and resolve it with
    context instead of guessing. Most forms map to exactly one id.
    Example: {"laxmi prasanna": ["person_006"], "kukatpalli": ["place_002"], ...}
    """
    forms: dict[str, list[str]] = defaultdict(list)
    for e in _load_cached():
        for form in e.surface_forms:
            key = _normalise(form)
            if e.id not in forms[key]:
                forms[key].append(e.id)
    return dict(forms)


def clear_cache() -> None:
    """Forget the cached KB, e.g. after editing the JSON files while the server is running."""
    _load_cached.cache_clear()
    _index_by_id.cache_clear()
