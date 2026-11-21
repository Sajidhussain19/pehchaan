"""
app/decide/lexicons.py — the small word lists the decision layer reasons with.

WHAT: - role_clues(): clue word -> role ("tooth" -> dentist), from data/lexicon/role_clues.json
      - clue_score(candidate, sentence): how strongly a sentence's clue words point at one candidate
        (+1 if a clue's role is one of the candidate's roles, +2 if the clue phrase is in the
        candidate's own notes/relation, e.g. "income tax" in "Files income tax")
      - expected_types(sentence): what KIND of entity the sentence wants ("table" -> a restaurant)
      - fits_type(entity, expected): does this entity fit that kind?
      - unfamiliar_names(heard): Indian first names in the heard text that are NOT the user's KB names
WHY:  These are the "context" in "a name must fit the context". Kept as plain data files, so a judge
      (or the developer) can read and extend them without touching code.
"""

import json
import re
from functools import lru_cache

from app.config import PROJECT_ROOT
from app.kb.loader import get_by_type, per_book_cache
from app.match.candidates import form_index
from app.match.phonetic import indian_phonetic_key, normalise
from app.match.spans import STOPWORDS, is_common

LEXICON = PROJECT_ROOT / "data" / "lexicon"
DOCTOR_ROLES = {"doctor", "dentist", "eye specialist", "general physician", "gynaecologist", "cardiologist",
                "dermatologist", "ent specialist", "paediatrician", "orthopaedic surgeon", "ophthalmologist"}


def _has_phrase(text_norm: str, phrase: str) -> bool:
    """Whole-word phrase match on normalised text ("ac" must not match inside "back")."""
    return re.search(rf"\b{re.escape(normalise(phrase))}\b", text_norm) is not None


@lru_cache(maxsize=1)
def role_clues() -> dict[str, list[str]]:
    data = json.loads((LEXICON / "role_clues.json").read_text(encoding="utf-8"))
    return {role: words for role, words in data.items() if not role.startswith("_")}


@lru_cache(maxsize=1)
def type_clues() -> dict[str, list[str]]:
    data = json.loads((LEXICON / "type_clues.json").read_text(encoding="utf-8"))
    return {kind: words for kind, words in data.items() if not kind.startswith("_")}


@lru_cache(maxsize=1)
def indian_first_names() -> frozenset[str]:
    names = set()
    for line in (LEXICON / "indian_first_names.txt").read_text(encoding="utf-8").splitlines():
        if not line.startswith("#"):
            names.update(line.split())
    return frozenset(names)


@per_book_cache  # one cached copy per contact book (Module 9)
def kb_name_words() -> frozenset[str]:
    """Every word that is part of some KB name or alias (so "Harshil" or "Mehta" count as known)."""
    return frozenset(w for f in form_index()[0] for w in f.text.split())


def clues_in(sentence_norm: str, exclude: str = "") -> list[tuple[str, str]]:
    """[(clue phrase, role)] found in the sentence, ignoring the words of `exclude` (the span itself)."""
    text = sentence_norm.replace(normalise(exclude), " ") if exclude else sentence_norm
    return [(phrase, role) for role, phrases in role_clues().items() for phrase in phrases if _has_phrase(text, phrase)]


def clue_score(entity, clues: list[tuple[str, str]], sentence_norm: str = "") -> tuple[int, list[str]]:
    """How strongly the sentence points at this entity, with the reasons:
    +1 per clue whose role the entity has ("tooth" -> dentist), +2 per clue phrase found in the entity's
    own relation/notes ("income tax" in "Files income tax"), +2 per rarer sentence word in those notes
    ("Warangal" in Ravi Teja's "Lives in Warangal")."""
    roles = set(entity.context.get("roles", []))
    own_text = normalise(f"{entity.context.get('relation', '')} {entity.context.get('notes', '')}")
    score, why = 0, []
    for phrase, role in clues:
        if role in roles:
            score += 1
            why.append(f"clue '{phrase}' -> {role}")
        if _has_phrase(own_text, phrase):
            score += 2
            why.append(f"clue '{phrase}' in their notes")
    # Rarer sentence words in their notes, compared by SOUND, so a transliterated "vaarangal" matches
    # "Lives in Warangal". Words of the relation ("college friend") count even if they're common English.
    name_words = set(normalise(entity.name).split())
    notes_keys = {indian_phonetic_key(w): w for w in normalise(entity.context.get("notes", "")).split() if len(w) >= 4}
    relation_words = {w for w in normalise(entity.context.get("relation", "")).split() if len(w) >= 4}
    for word in sorted(set(sentence_norm.split()) - name_words):
        if len(word) < 4 or word in STOPWORDS:
            continue
        if word in relation_words:
            score += 2
            why.append(f"'{word}' fits their relation ({entity.context['relation']})")
        elif not is_common(word) and indian_phonetic_key(word) in notes_keys:
            score += 2
            why.append(f"'{word}' matches their notes ('{notes_keys[indian_phonetic_key(word)]}')")
    return score, why


def expected_types(sentence_norm: str) -> list[tuple[str, str]]:
    """[(kind, clue word)] such as ("business:restaurant", "table")."""
    return [(kind, word) for kind, words in type_clues().items() for word in words if _has_phrase(sentence_norm, word)]


def fits_type(entity, expected: list[tuple[str, str]]) -> bool:
    """Does the entity fit what the sentence asks for? Places always fit (they're just "where")."""
    if not expected or entity.type == "place":
        return True
    for kind, _ in expected:
        for option in kind.split("|"):  # "person:doctor|business:clinic" = either is fine
            etype, _, sub = option.partition(":")
            if etype != entity.type:
                continue
            if etype == "business" and entity.context["category"] == sub:
                return True
            if etype == "person" and sub == "doctor" and (set(entity.context.get("roles", [])) & DOCTOR_ROLES
                                                          or entity.name.startswith("Dr")):
                return True
    return False


def unfamiliar_names(heard: str) -> list[str]:
    """Indian first names in the heard text that are NOT part of any KB name ("Sravanthi", "Rohan")."""
    return [w for w in normalise(heard).split() if w in indian_first_names() and w not in kb_name_words()]
