"""
app/match/candidates.py — scores KB entities for every possible span and keeps the best spans.

WHAT: find_candidates(transcript) -> list[Span], sorted by position. Each Span has:
        start/end (character offsets), heard_text, kind ("name" | "reference"), type_hint,
        candidates: up to 3 x {entity_id, name, score, phonetic, fuzzy, reasons}, and
        margin = top score - second score (a small margin means "two candidates are close").
      Steps:
        1. Build an index of every way a KB entity can be written ("forms"): canonical name, aliases,
           the name without honorifics ("Venkataramana" for "Dr. Venkataramana"), and for people
           the first name alone and first + surname.
        2. For each name span: shortlist forms quickly (RapidFuzz on sound keys + exact Metaphone
           matches), then score each shortlisted form fully (weights in app/match/config.py).
        3. Keep the top 3 entities per span, drop weak spans, then non-max suppression: keep the
           best-scoring spans that don't overlap. Reference spans ("my doctor") always win their words.
WHY:  This is Pehchaan's "ears" (Modules 6+7), with no LLM and no decisions. Module 8 decides,
      from these scores and margins, whether to resolve, ask, or keep.
"""

import time
from dataclasses import dataclass
from functools import lru_cache

from pydantic import BaseModel
from rapidfuzz import fuzz, process

from app.kb.loader import get_by_id, load_kb
from app.match.config import DEFAULT, MatchWeights
from app.match.phonetic import indian_phonetic_key, metaphone_keys, metaphone_similarity, normalise, INDIAN_KEY_SHARE
from app.match.spans import RawSpan, name_spans, reference_spans, tokenize

LEADING_HONORIFICS = {"dr", "doctor", "smt", "sri", "shri", "sree", "shree", "fr", "father", "sister", "sr",
                      "mr", "mrs", "ms"}  # "Father Anthony Raj" must not give the first name "father"
TRAILING_HONORIFICS = {"garu", "anna", "ji", "akka"}


class Candidate(BaseModel):
    entity_id: str
    name: str  # canonical name, for display
    score: float  # final 0-1 score
    phonetic: float  # sound similarity of the best-matching form
    fuzzy: float  # spelling similarity of the best-matching form
    reasons: list[str]


class Span(BaseModel):
    start: int
    end: int
    heard_text: str
    kind: str  # "name" | "reference"
    type_hint: str | None
    candidates: list[Candidate]
    margin: float  # top1 score - top2 score (1.0 if only one candidate)


@dataclass(frozen=True)
class Form:
    entity_id: str
    text: str  # e.g. "venkataramana"
    key: str  # indian_phonetic_key(text)
    entity_type: str


def _strip_honorifics(words: list[str]) -> list[str]:
    while words and words[0] in LEADING_HONORIFICS:
        words = words[1:]
    while words and words[-1] in TRAILING_HONORIFICS:
        words = words[:-1]
    return words


@lru_cache(maxsize=1)
def form_index() -> tuple[list[Form], dict[str, list[int]]]:
    """All forms, plus a lookup from Metaphone code -> form positions (for exact sound matches)."""
    forms: list[Form] = []
    seen = set()
    for e in load_kb():
        texts = set()
        for surface in (e.name, *e.aliases):
            words = normalise(surface).split()
            texts.add(" ".join(words))
            bare = _strip_honorifics(words)
            if bare:
                texts.add(" ".join(bare))
                if e.type == "person":
                    texts.add(bare[0])  # first name alone: "Harshit"
                    if len(bare) > 2:
                        texts.add(f"{bare[0]} {bare[-1]}")  # first + surname: "Bibhuti Sahoo"
        for t in texts:
            if t and (e.id, t) not in seen:
                seen.add((e.id, t))
                forms.append(Form(e.id, t, indian_phonetic_key(t), e.type))
    by_metaphone: dict[str, list[int]] = {}
    for idx, f in enumerate(forms):
        for code in metaphone_keys(f.text):
            by_metaphone.setdefault(code, []).append(idx)
    return forms, by_metaphone


@lru_cache(maxsize=1)
def _form_keys() -> list[str]:
    return [f.key for f in form_index()[0]]


def score_form(span: RawSpan, span_text: str, span_key: str, form: Form, w: MatchWeights) -> tuple[float, float, float, list[str]]:
    """Full score of one form for one span: (score, phonetic, fuzzy, reasons)."""
    indian = fuzz.ratio(span_key, form.key) / 100
    phonetic = INDIAN_KEY_SHARE * indian + (1 - INDIAN_KEY_SHARE) * metaphone_similarity(span_text, form.text)
    fuzzy = fuzz.ratio(span_text, form.text) / 100
    score = (w.w_phonetic * phonetic + w.w_fuzzy * fuzzy) / (w.w_phonetic + w.w_fuzzy)
    reasons = [f"sounds {phonetic:.2f}", f"spelling {fuzzy:.2f}"]

    # Length: "a" can't really be "Abids"; very different lengths make a match unlikely.
    length_ratio = min(len(span_key), len(form.key)) / max(len(span_key), len(form.key), 1)
    if length_ratio < 1:
        score -= w.length_penalty * (1 - length_ratio)
        if length_ratio < 0.7:
            reasons.append(f"length mismatch ({length_ratio:.2f})")

    # Context: does the surrounding sentence agree with this kind of entity?
    if span.type_hint == "person":
        agrees = form.entity_type == "person"
    elif span.type_hint == "location":
        agrees = form.entity_type in ("place", "business")
    else:
        agrees = None
    if agrees is True:
        score += w.type_bonus
        reasons.append(f"context fits {form.entity_type}")
    elif agrees is False:
        score -= w.type_penalty
        reasons.append(f"context suggests {span.type_hint}, not {form.entity_type}")

    # Ordinary English: "lucky", "a bit", "said". Full penalty unless the transcript spells this
    # exact name (then it IS the name, e.g. "Holy Family Clinic", all common words but a real KB name).
    if span.all_common and span_text != form.text:
        score -= w.common_penalty
        reasons.append(f"common English words (-{w.common_penalty:.2f})")
    if span.capitalised:
        score += w.capital_bonus
    return max(0.0, min(1.0, score)), phonetic, fuzzy, reasons


def _score_name_span(span: RawSpan, w: MatchWeights) -> list[Candidate]:
    forms, by_metaphone = form_index()
    span_text = " ".join(t.norm for t in span.tokens)
    span_key = indian_phonetic_key(span_text)
    if len(span_key) < 3:
        return []  # one or two letters can't be matched reliably

    # Shortlist: closest sound keys (fast C search) + any form with the SAME Metaphone code
    # (catches "cook at polly" == "Kukatpally" even if the key ratio is mediocre).
    shortlist = {idx for _, _, idx in process.extract(span_key, _form_keys(), scorer=fuzz.ratio, limit=w.shortlist)}
    for code in metaphone_keys(span_text):
        shortlist.update(by_metaphone.get(code, []))

    best: dict[str, tuple] = {}
    for idx in shortlist:
        form = forms[idx]
        if len(form.key) <= 3 and form.key != span_key:
            continue  # tiny forms ("Sid", "Sai", "Mou") only match exactly: "said" is not "Sid"
        result = score_form(span, span_text, span_key, form, w)
        if form.entity_id not in best or result[0] > best[form.entity_id][0]:
            best[form.entity_id] = (*result, form.text)

    ranked = sorted(best.items(), key=lambda kv: kv[1][0], reverse=True)[: w.top_k]
    return [Candidate(entity_id=eid, name=get_by_id(eid).name, score=round(s, 3), phonetic=round(p, 3),
                      fuzzy=round(f, 3), reasons=[f"matches form '{form_text}'", *r])
            for eid, (s, p, f, r, form_text) in ranked]


def _overlaps(a: Span, b: Span) -> bool:
    return a.start < b.end and b.start < a.end


def find_candidates(transcript: str, weights: MatchWeights = DEFAULT) -> list[Span]:
    """All name and reference spans with their candidates, non-overlapping, in text order."""
    tokens = tokenize(transcript)
    kept: list[Span] = []

    # 1. Personal references first: exact phrase rules, they always keep their words.
    for raw in reference_spans(tokens):
        cands = [Candidate(entity_id=eid, name=get_by_id(eid).name, score=1.0, phonetic=0.0, fuzzy=0.0, reasons=r)
                 for eid, r in raw.reference_candidates]
        span = Span(start=raw.start, end=raw.end, heard_text=transcript[raw.start:raw.end], kind="reference",
                    type_hint=None, candidates=cands, margin=1.0 if len(cands) == 1 else 0.0)
        if cands and not any(_overlaps(span, k) for k in kept):
            kept.append(span)

    # 2. Name spans: score, drop weak ones, then non-max suppression (best first, no overlaps).
    scored: list[Span] = []
    for raw in name_spans(tokens, weights.max_tokens):
        cands = _score_name_span(raw, weights)
        if not cands or cands[0].score < weights.min_span_score:
            continue
        cands[0].reasons.extend(raw.features)
        margin = cands[0].score - (cands[1].score if len(cands) > 1 else 0.0)
        scored.append(Span(start=raw.start, end=raw.end, heard_text=transcript[raw.start:raw.end], kind="name",
                           type_hint=raw.type_hint, candidates=cands, margin=round(margin, 3)))
    # Ties go to the longer span ("Thirumalai Selvan" beats "Selvan" at equal score).
    for span in sorted(scored, key=lambda s: (s.candidates[0].score, s.end - s.start), reverse=True):
        if not any(_overlaps(span, k) for k in kept):
            kept.append(span)
    return sorted(kept, key=lambda s: s.start)


def timed_find_candidates(transcript: str, weights: MatchWeights = DEFAULT) -> tuple[list[Span], float]:
    """find_candidates plus how long it took, in milliseconds."""
    start = time.perf_counter()
    spans = find_candidates(transcript, weights)
    return spans, (time.perf_counter() - start) * 1000
