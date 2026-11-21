"""
app/match/spans.py — finds the parts of a transcript that MIGHT be names or personal references.

WHAT: - tokenize(text): words with their character positions (so we can point back into the text)
      - name_spans(tokens): every run of 1-4 words, with context features:
          * type hint: a place word before it ("in", "at", "from", "near", "to") -> place/business;
            a person cue nearby ("call", "tell", "ask", "remind", "message", "Dr", "Sri", "garu",
            "anna", "ji", "here", "speaking"...) -> person
          * capitalised? (speech-to-text capitalises what it thinks are names)
          * all common English words? ("a bit", "the cook": probably not a name)
      - reference_spans(tokens): personal references, matched exactly (no fuzziness needed):
          "my/the <role>" (my doctor, the electrician, my son's teacher), family labels (Amma, Nanna,
          Akka, Anna, Bhaiya...), "the usual <category>", "same <x> as last time".
          Each gets ALL the KB entities that fit, via the loader (get_by_role, get_by_family_label,
          get_usual_business).
WHY:  Speech-to-text splits names across words ("Aunt Johnny" for "Anjani"), so we can't trust
      word boundaries: we try every short run of words and let the scorer (candidates.py) decide.
"""

import re
from dataclasses import dataclass, field
from functools import lru_cache

from app.config import PROJECT_ROOT
from app.kb.loader import get_by_family_label, get_by_role, get_by_type, get_primary_for, get_usual_business
from app.match.phonetic import indian_phonetic_key, normalise
from app.match.translit import has_indic, transliterate

COMMON_WORDS_PATH = PROJECT_ROOT / "data" / "lexicon" / "common_english_words.txt"

# Words before a span that suggest a place or business: "in Kukatpally", "at Kakatiya Kitchen".
# Includes Hindi/Telugu postpositions seen in code-mixed speech ("Kukatpally nunchi" = from Kukatpally).
PLACE_PREPOSITIONS = {"in", "at", "from", "near", "to", "into", "nunchi", "se", "mein", "lo", "ki"}
# Words near a span that suggest a person.
PERSON_VERBS = {"call", "tell", "ask", "remind", "message", "text", "ping", "inform", "meet", "msg", "bolo",
                "contact", "wish", "pay", "with"}
HONORIFICS = {"dr", "doctor", "sri", "shri", "smt", "mr", "mrs", "ms", "anna", "garu", "ji", "sir", "madam",
              "bhaiya", "akka", "aunty", "auntie", "uncle", "saar", "fr", "father", "sister"}
PERSON_NEXT = {"here", "speaking", "ko", "ne", "garu", "ji", "anna"}  # "Sharma Ji here", "Ravi Teja ko call karo"
# Tiny words that are never names on their own (skip spans made only of these).
STOPWORDS = {"a", "an", "the", "to", "of", "in", "at", "on", "is", "and", "or", "for", "me", "my", "i", "you",
             "he", "she", "it", "we", "they", "be", "am", "are", "was", "if", "so", "do", "this", "that", "with",
             "by", "as", "up", "no", "not", "ok", "please", "and", "but", "ko", "ki", "ka", "ke", "hai", "se"}
# Category words after "the usual": what the user says -> what `usual_for` stores.
USUAL_WORDS = {"pharmacy": "pharmacy", "chemist": "pharmacy", "medical": "pharmacy", "medicals": "pharmacy",
               "kirana": "groceries", "grocery": "groceries", "groceries": "groceries", "provision": "groceries",
               "salon": "salon", "parlour": "salon", "parlor": "salon", "barber": "salon",
               "tiffin": "tiffins", "tiffins": "tiffins"}
TRAILING_NOUNS = {"shop", "store", "place", "centre", "center", "one"}  # "the usual kirana SHOP"


@dataclass
class Token:
    text: str  # as written in the transcript
    start: int  # character offsets into the transcript
    end: int
    norm: str  # normalised: lower case, Latin script, no possessive "'s"


@dataclass
class RawSpan:
    """A run of tokens before scoring."""

    start: int
    end: int
    heard_text: str
    tokens: list[Token]
    kind: str  # "name" or "reference"
    type_hint: str | None = None  # "person", "location" (place or business), or None
    capitalised: bool = False
    all_common: bool = False
    features: list[str] = field(default_factory=list)  # short human-readable notes
    reference_candidates: list[tuple[str, list[str]]] = field(default_factory=list)  # (entity_id, reasons)


@lru_cache(maxsize=1)
def common_words() -> frozenset[str]:
    """The ~3,300 common English words (data/lexicon/common_english_words.txt)."""
    words = set()
    for line in COMMON_WORDS_PATH.read_text(encoding="utf-8").splitlines():
        if not line.startswith("#"):
            words.update(line.split())
    return frozenset(words)


# Letters plus the Devanagari and Telugu blocks (so vowel signs stay inside their word),
# plus an optional possessive "'s".
_TOKEN_RE = re.compile(r"[A-Za-z0-9ऀ-ॿఀ-౿]+(?:'[A-Za-z]+)?")


def tokenize(text: str) -> list[Token]:
    tokens = []
    for m in _TOKEN_RE.finditer(text):
        raw = m.group()
        word = transliterate(raw) if has_indic(raw) else raw
        word = re.sub(r"'s$", "", word.lower())  # "Amma's" -> "amma"
        tokens.append(Token(raw, m.start(), m.end(), normalise(word)))
    return tokens


def _type_hint(tokens: list[Token], i: int, j: int) -> tuple[str | None, list[str]]:
    """Context clues around tokens[i:j] (j exclusive)."""
    notes = []
    prev = tokens[i - 1].norm if i > 0 else ""
    nxt = tokens[j].norm if j < len(tokens) else ""
    before = {t.norm for t in tokens[max(0, i - 3):i]}
    if prev in PLACE_PREPOSITIONS:
        notes.append(f"after '{prev}' -> place/business")
        return "location", notes
    if prev in HONORIFICS or nxt in HONORIFICS or nxt in PERSON_NEXT:
        notes.append(f"next to '{prev if prev in HONORIFICS else nxt}' -> person")
        return "person", notes
    if before & PERSON_VERBS:
        notes.append(f"near '{sorted(before & PERSON_VERBS)[0]}' -> person")
        return "person", notes
    if {"this", "is"} <= before or "im" in before or "i" in before and "am" in before:
        notes.append("self-introduction -> person")
        return "person", notes
    return None, notes


def name_spans(tokens: list[Token], max_tokens: int = 4) -> list[RawSpan]:
    """Every run of 1..max_tokens words that isn't made only of tiny stopwords."""
    common = common_words()
    spans = []
    for i in range(len(tokens)):
        for j in range(i + 1, min(i + max_tokens, len(tokens)) + 1):
            chunk = tokens[i:j]
            norms = [t.norm for t in chunk]
            if all(n in STOPWORDS for n in norms):
                continue
            hint, notes = _type_hint(tokens, i, j)
            # Capitalised words that are NOT just the first word of the sentence.
            capitalised = all(t.text[:1].isupper() for t in chunk) and not (i == 0 and j == 1)
            all_common = all(n in common or n in STOPWORDS for n in norms)
            if capitalised:
                notes.append("capitalised")
            if all_common:
                notes.append("all common English words")
            spans.append(RawSpan(chunk[0].start, chunk[-1].end, "", chunk, "name", hint, capitalised, all_common, notes))
    return spans


@lru_cache(maxsize=1)
def _role_phrases() -> dict[tuple[str, ...], str]:
    """Every role in the KB as normalised word tuples: ("son", "teacher") -> "son's teacher"."""
    roles = {r for e in get_by_type("person") for r in e.context.get("roles", [])}
    return {tuple(normalise(r.replace("'s", "")).split()): r for r in roles}


@lru_cache(maxsize=1)
def _family_labels() -> dict[str, str]:
    """Family words keyed by SOUND, so Telugu "నాన్న" (transliterated "naanna") still finds "Nanna"."""
    return {indian_phonetic_key(e.context["family_label"]): e.context["family_label"]
            for e in get_by_type("person") if e.context.get("family_label")}


def _family_label_of(word: str) -> str | None:
    """The family label this word sounds like, also allowing a dropped apostrophe ("Amas" = "Amma's")."""
    labels = _family_labels()
    key = indian_phonetic_key(word)
    if key in labels:
        return labels[key]
    if key.endswith("s") and key[:-1] in labels:
        return labels[key[:-1]]
    return None


def _role_candidates(role: str) -> list[tuple[str, list[str]]]:
    """All contacts with this role, with notes Module 8 can use (default? last talked when?)."""
    default = get_primary_for(role)
    out = []
    for e in get_by_role(role):
        reasons = [f"role: {role}"]
        if default and default.id == e.id:
            reasons.append(f"DEFAULT for {role}")
        if e.context.get("last_interaction"):
            reasons.append(f"last interaction {e.context['last_interaction']}")
        out.append((e.id, reasons))
    return out


def reference_spans(tokens: list[Token]) -> list[RawSpan]:
    """Personal references found by exact phrase rules (no fuzzy matching needed)."""
    spans: list[RawSpan] = []
    norms = [t.norm for t in tokens]
    common = common_words()
    roles = _role_phrases()
    longest_role = max(len(k) for k in roles)

    def add(i, j, candidates, note):
        spans.append(RawSpan(tokens[i].start, tokens[j - 1].end, "", tokens[i:j], "reference",
                             features=[note], reference_candidates=candidates))

    for i, word in enumerate(norms):
        # "my doctor", "my son's teacher": longest matching role wins. "the <role>" only counts
        # after a request verb ("Call THE ELECTRICIAN"); otherwise "The cook at the polling booth"
        # would wrongly become a reference to the user's cook.
        prev_word = norms[i - 1] if i > 0 else ""
        if word in ("my", "our") or (word == "the" and prev_word in PERSON_VERBS):
            for n in range(longest_role, 0, -1):
                key = tuple(norms[i + 1:i + 1 + n])
                if len(key) == n and key in roles:
                    add(i, i + 1 + n, _role_candidates(roles[key]), f"'{word} <role>' -> role '{roles[key]}'")
                    break
        # "the usual pharmacy", "the usual kirana shop"
        if word == "usual" and i + 1 < len(norms) and norms[i + 1] in USUAL_WORDS:
            need = USUAL_WORDS[norms[i + 1]]
            start = i - 1 if i > 0 and norms[i - 1] in ("the", "my", "our") else i
            end = i + 2 + (1 if i + 2 < len(norms) and norms[i + 2] in TRAILING_NOUNS else 0)
            biz = get_usual_business(need)
            cands = [(biz.id, [f"USUAL for {need}"])] if biz else []
            add(start, end, cands, f"'the usual {norms[i + 1]}' -> usual {need}")
        # "same doctor as last time": the role/category, ordered by most recent interaction.
        if word == "same" and i + 1 < len(norms):
            for n in range(longest_role, 0, -1):
                key = tuple(norms[i + 1:i + 1 + n])
                end = i + 1 + n
                if key in roles and norms[end:end + 3] == ["as", "last", "time"]:
                    cands = sorted(_role_candidates(roles[key]),
                                   key=lambda c: next((r for r in c[1] if r.startswith("last")), ""), reverse=True)
                    add(i, end + 3, cands, f"'same {roles[key]} as last time' -> most recent first")
                    break
        # Family words: "Amma", "Nanna", "Bhaiya". "Anna" right after a name is a respectful
        # suffix ("Ramulu Anna" = brother Ramulu, the vendor), not the user's own elder brother.
        label = _family_label_of(word)
        if label:
            prev = norms[i - 1] if i > 0 else ""
            if label == "Anna" and prev and prev not in common and prev not in STOPWORDS:
                continue
            person = get_by_family_label(label)
            add(i, i + 1, [(person.id, [f"family label: {label}"])], f"family word '{label}'")
    return spans
