"""
app/decide/graph.py — Pehchaan's decision pipeline, built with LangGraph (one node per step).

WHAT: START -> preferences -> candidates -> references -> context_check -> route
            -> (llm_fallback, ONLY if some span is still unsure) -> action -> assemble -> END
      Each node reads the shared state and records, per span: resolve / keep / clarify, the entity,
      a confidence and a human-readable reason ("heard -> resolved -> confidence -> reason").
        1. preferences   learned answers ("always use Harshil for 'my colleague'") come first
        2. candidates    Modules 6+7: spans + scored candidates (no LLM)
        3. references    "my doctor", "Amma", "the usual pharmacy": clue words FIRST, then the user's
                         default, else ask. A clue that contradicts the default wins.
        4. context_check the name must fit the context: an unknown caller saying "I'm Raju" is not
                         your Dr. Raju; "book a table at Raju Hotel" can't silently become a doctor
        5. route         confidence routing for names: clear winner -> resolve; close call -> clue
                         tie-break or ask; middling score -> LLM; weak -> keep. Plus the
                         unfamiliar-name guard ("Sravanthi" is a real name, not a typo for "Sravani").
        6. llm_fallback  one small gpt-4o-mini call for the unsure spans only
        7. action        the Remind action: who, where, and when ("HH:MM"), with rules
        8. assemble      the final Decision (same format as baseline (c))
WHY:  A graph makes the order of reasoning explicit and inspectable. The LLM is a side branch,
      not the main road, so most clips are decided in milliseconds for $0.
"""

import re
import time
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from app.decide import lexicons
from app.decide.config import DEFAULT, DecideConfig
from app.decide.llm_fallback import ask_llm
from app.eval.decision import ActionDecision, Decision, EntityDecision
from app.eval.timeparse import normalise_time
from app.kb.loader import get_by_id, load_preferences
from app.match.candidates import Span, find_candidates
from app.match.phonetic import indian_phonetic_key, normalise, phonetic_similarity
from app.match.translit import has_indic, transliterate

# Words that mean "the user wants something done" (outgoing commands, incl. Hindi/Telugu).
INTENT_WORDS = {"remind", "call", "tell", "ask", "message", "text", "book", "order", "send", "pick", "visit",
                "meet", "pay", "wish", "collect", "bring", "inform", "get", "wake", "bolo", "cheyyi", "karo",
                "msg", "ping", "buy", "take", "drop", "keep", "move", "reschedule", "confirm", "check",
                # Telugu / Hindi, as they look after transliteration ("కాల్ చేయి" -> "kaal cheeyi")
                "cheyi", "cheeyi", "chey", "cheyandi", "kaal", "kol", "kar", "bol", "pucho", "poocho", "batao",
                "bhejo", "adugu", "adagandi", "cheppu", "pampu"}
# Words that make an incoming call worth a reminder (it sets up something at a time).
TIME_WORDS = {"tomorrow", "today", "tonight", "morning", "evening", "afternoon", "night", "monday", "tuesday",
              "wednesday", "thursday", "friday", "saturday", "sunday", "kal", "subah", "shaam", "baje", "am", "pm",
              "appointment", "meeting", "review"}
SELF_INTRO_BEFORE = ("this is", "i am", "im", "my name is", "i m")
SELF_INTRO_AFTER = {"here", "speaking", "calling"}
HONORIFIC_WORDS = {"dr", "doctor", "smt", "sri", "fr", "father", "sister", "mr", "mrs"}
# How each kind of resolution maps to the sentence-level behaviour the evaluator expects.
NEEDS_CONTEXT = {"clue", "default", "label", "usual", "preference", "tiebreak", "recent"}


class Item(BaseModel):
    """One span and what we decided about it."""

    span: Span
    status: str = "undecided"  # undecided | resolve | keep | clarify | llm
    entity_id: str | None = None
    confidence: float = 0.0
    reason: str = ""
    how: str = ""  # exact | high | clue | default | label | usual | preference | tiebreak | caller | llm | ...
    clarify_ids: list[str] = []

    def set(self, status, how, reason, entity_id=None, confidence=None, clarify_ids=()):
        self.status, self.how, self.reason, self.entity_id = status, how, reason, entity_id
        top = self.span.candidates[0].score if self.span.candidates else 0.0
        self.confidence = round(confidence if confidence is not None else (top if status != "keep" else 1 - top), 3)
        self.clarify_ids = list(clarify_ids)


class State(TypedDict, total=False):
    transcript: str
    direction: str
    caller_contact_id: str | None
    clip_id: str
    config: DecideConfig
    preferences: list | None  # None = read data/kb/preferences.json
    client: Any  # OpenAI client (a fake in tests)
    started: float
    pref_map: dict
    norm: str
    items: list[Item]
    used_llm: bool
    cost_usd: float
    llm_latency_ms: float
    action: ActionDecision
    decision: Decision


# ---------------------------------------------------------------------------
# 1. preferences: learned answers come first
# ---------------------------------------------------------------------------
def preferences_node(state: State) -> dict:
    """Example: after the user chose "Always use Harshil for 'my colleague'", the phrase
    "my colleague" maps straight to Harshil, no question asked."""
    prefs = state.get("preferences")
    prefs = load_preferences() if prefs is None else prefs
    # Later preferences win if a phrase was learned twice.
    pref_map = {p.phrase_pattern: p.entity_id for p in sorted(prefs, key=lambda p: p.created_at)}
    return {"pref_map": pref_map}


# ---------------------------------------------------------------------------
# 2. candidates: Modules 6+7
# ---------------------------------------------------------------------------
def candidates_node(state: State) -> dict:
    """Example: "Call Aunt Johnny" -> span "Aunt Johnny" with candidates Anthony / Manjunath / Anjani."""
    spans = find_candidates(state["transcript"])
    return {"items": [Item(span=s) for s in spans], "norm": normalise(state["transcript"]),
            "used_llm": False, "cost_usd": 0.0, "llm_latency_ms": 0.0}


# ---------------------------------------------------------------------------
# 3. references: clue -> saved preference -> default -> ask
# ---------------------------------------------------------------------------
def references_node(state: State) -> dict:
    """Example: "Call my doctor, my tooth is paining": the clue "tooth" picks the dentist over the default
    family doctor. "Call my doctor": no clue, so the default. "Ask my colleague": 19 people, no clue,
    no default, so ask."""
    for item in state["items"]:
        span = item.span
        if span.kind != "reference":
            continue
        heard = normalise(span.heard_text)
        cands = span.candidates
        if len(cands) == 1:
            how = "label" if any("family label" in r for r in cands[0].reasons) else "usual"
            item.set("resolve", how, "; ".join(cands[0].reasons), cands[0].entity_id, 0.95)
            continue
        if heard.startswith("same "):  # "same doctor as last time": most recent first
            item.set("resolve", "recent", "same as last time: most recent interaction", cands[0].entity_id, 0.8)
            continue
        clues = lexicons.clues_in(state["norm"], exclude=span.heard_text)
        rest = _without_span(state, span)  # round 3: "my DOCTOR" must not count as a clue for "family DOCTOR"
        scored = [(lexicons.clue_score(get_by_id(c.entity_id), clues, rest), c) for c in cands]
        best = max(s for (s, _), _ in scored)
        pool = [c for (s, _), c in scored if s == best] if best > 0 else cands
        if best > 0 and len(pool) == 1:
            why = next(w for (s, w), c in scored if c is pool[0])
            # Module 10 (approved change after final-eval-v1): a clue in the sentence beats a saved preference,
            # just as it beats a default. "Always use the dentist for 'my doctor'" must not send
            # "call my doctor about my fever" to the dentist.
            note = "; beats your saved choice" if state["pref_map"].get(heard) not in (None, pool[0].entity_id) else ""
            item.set("resolve", "clue", "; ".join(why) + note, pool[0].entity_id, 0.9)
            continue
        if heard in state["pref_map"]:  # no deciding clue: what the user taught us comes before the default
            item.set("resolve", "preference", f"you told me '{heard}' means this", state["pref_map"][heard], 0.99)
            continue
        default = next((c for c in pool if any(r.startswith("DEFAULT") for r in c.reasons)), None)
        if default:
            item.set("resolve", "default", next(r for r in default.reasons if r.startswith("DEFAULT")),
                     default.entity_id, 0.85)
        else:
            item.set("clarify", "ambiguous", f"{len(pool)} people fit '{span.heard_text}' and nothing in the "
                     "sentence separates them", clarify_ids=[c.entity_id for c in pool], confidence=0.5)
    return {"items": state["items"]}


# ---------------------------------------------------------------------------
# 4. context_check: caller and entity type must fit
# ---------------------------------------------------------------------------
def _is_self_intro(state: State, span: Span) -> bool:
    before = normalise(state["transcript"][:span.start])
    after = normalise(state["transcript"][span.end:]).split()
    return any(before.endswith(p) for p in SELF_INTRO_BEFORE) or (bool(after) and after[0] in SELF_INTRO_AFTER)


def context_check_node(state: State) -> dict:
    """Examples: an UNKNOWN number saying "Hi, I'm Raju from the bank" is not the user's Dr. Raju -> keep.
    "Book a table at Raju Hotel": 'table' needs a restaurant, Dr. Raju is a person -> ask, don't resolve."""
    cfg = state["config"]
    expected = lexicons.expected_types(state["norm"])
    caller = get_by_id(state["caller_contact_id"]) if state.get("caller_contact_id") else None
    for item in state["items"]:
        span = item.span
        if item.status != "undecided" or span.kind != "name":
            continue
        top = span.candidates[0]
        entity = get_by_id(top.entity_id)
        if state["direction"] == "incoming" and _is_self_intro(state, span) and entity.type == "person":
            if caller and (caller.id in {c.entity_id for c in span.candidates}
                           or phonetic_similarity(span.heard_text, caller.name) >= cfg.low):
                item.set("resolve", "caller", f"the call comes from {caller.name}'s saved number", caller.id, 0.97)
            elif not caller:
                item.set("keep", "unknown_caller", f"an unknown number introducing themself as '{span.heard_text}' "
                         f"is a different person, not your {entity.name}")
            continue
        head = _business_word_next_to(state, span)
        owner = span.heard_text.rstrip().endswith(("'s", "’s"))  # "Dr. Venkataramana's clinic": the OWNER
        if head and entity.type != "business" and not owner:
            # Round 3: "Mansoor Tailors" is a business we don't know; it can't silently become Mysuru.
            if entity.type == "person" and top.score >= cfg.high:
                item.set("clarify", "type_mismatch", f"'{span.heard_text} {head}' sounds like a business, but "
                         f"{entity.name} is your {entity.context.get('relation', 'contact')}: asking instead of guessing",
                         clarify_ids=[top.entity_id])
            else:
                item.set("keep", "type_mismatch", f"'{head}' next to it means an unknown business, not {entity.name}")
            continue
        if expected and not lexicons.fits_type(entity, expected):
            kind, word = expected[0]
            what = kind.split("|")[0].replace(":", " ")
            if top.score >= cfg.high:
                close = [c.entity_id for c in span.candidates
                         if c.score >= top.score - cfg.margin and get_by_id(c.entity_id).type != "place"]
                item.set("clarify", "type_mismatch", f"'{word}' needs a {what}, but {entity.name} is your "
                         f"{entity.context.get('relation', entity.type)}: asking instead of guessing", clarify_ids=close)
            else:
                item.set("keep", "type_mismatch", f"'{word}' needs a {what}; {entity.name} doesn't fit")
    return {"items": state["items"]}


# ---------------------------------------------------------------------------
# 5. route: confidence routing for names
# ---------------------------------------------------------------------------
def _is_exact_full_name(span: Span) -> bool:
    """Heard text is exactly the entity's full name or a multi-word alias ("Ravi Teja", "Kukatpally"),
    not just a first name ("Harshit") that a near-identical contact could share."""
    top = span.candidates[0]
    heard, form = normalise(span.heard_text), normalise(top.form)
    if heard != form and heard != form + "s":  # allow a possessive: "Venkataramana's"
        return False
    return form == normalise(get_by_id(top.entity_id).name) or len(form.split()) >= 2


BUSINESS_WORDS = {"tailors", "tailor", "hotel", "salon", "saloon", "store", "stores", "bakery", "restaurant", "dhaba",
                  "hospital", "clinic", "school", "opticals", "jewellers", "medicals", "pharmacy", "kitchen",
                  "travels", "motors", "traders", "enterprises", "mart", "sweets", "bhavan", "mess", "studio",
                  "parlour", "dhaba", "cafe", "bhandar", "agencies", "electricals", "hardware"}


def _without_span(state: State, span: Span) -> str:
    """The normalised sentence with this span's own words removed."""
    t = state["transcript"]
    return normalise(t[:span.start] + " " + t[span.end:])


def _business_word_next_to(state: State, span: Span) -> str | None:
    """A business word right after ("Mansoor TAILORS") or right before ("HOTEL Subramanian") the span."""
    after = normalise(state["transcript"][span.end:]).split()
    before = normalise(state["transcript"][:span.start]).split()
    if after and after[0] in BUSINESS_WORDS:
        return after[0]
    if before and before[-1] in BUSINESS_WORDS:
        return before[-1]
    return None


def _areas_of_confident_businesses(state: State, span: Span) -> dict[str, str]:
    """{area name: business name} for businesses confidently heard elsewhere in the same sentence."""
    out = {}
    for other in state["items"]:
        if other.span is span or other.span.kind != "name" or not other.span.candidates:
            continue
        top = other.span.candidates[0]
        entity = get_by_id(top.entity_id)
        if entity.type == "business" and top.score >= state["config"].high:
            out[entity.context["area"]] = entity.name
    return out


def _is_action_target(state: State, span: Span) -> bool:
    before = set(normalise(state["transcript"][:span.start]).split())
    return span.type_hint == "person" or bool(before & INTENT_WORDS)


def route_node(state: State) -> dict:
    """Examples: "Kukatpally" exact -> resolve. "Call Harshit at 5": Harshit/Harshil too close, no clue -> ask.
    "Ask Harshel to send the invoice": close, but 'invoice' -> accounts -> Harshil. "Sravanthi": a real name
    that isn't a contact -> never silently Sravani. "Aunt Johnny" 0.7 -> let the LLM judge."""
    cfg = state["config"]
    for item in state["items"]:
        span = item.span
        if item.status != "undecided" or span.kind != "name":
            continue
        heard = normalise(span.heard_text)
        top = span.candidates[0]
        if heard in state["pref_map"]:
            item.set("resolve", "preference", f"you told me '{heard}' means this", state["pref_map"][heard], 0.99)
            continue
        if top.score >= cfg.high and _is_exact_full_name(span):
            item.set("resolve", "exact", f"heard exactly '{top.form}'", top.entity_id)
            continue
        unfamiliar = lexicons.unfamiliar_names(span.heard_text)
        if unfamiliar and normalise(top.form) != heard:
            # Round 1: only ask if the nearby contact is a STRONG match ("Sravanthi" ~ Sravani 0.97);
            # "Abhinav" ~ Pranav 0.7 is just someone else -> keep.
            if _is_action_target(state, span) and top.score >= cfg.high:
                ids = [c.entity_id for c in span.candidates if c.score >= cfg.low][:2]
                item.set("clarify", "unfamiliar", f"'{unfamiliar[0].title()}' is a real name that isn't in your "
                         f"contacts: maybe someone new, maybe {top.name}?", clarify_ids=ids or [top.entity_id])
            else:
                item.set("keep", "unfamiliar", f"'{unfamiliar[0].title()}' is a real name that isn't in your contacts")
            continue
        if has_indic(span.heard_text) and top.score < cfg.high:
            # Round 3: a garbled Telugu/Devanagari word ("నన్నొత్తి") led the LLM to a wrong person.
            item.set("keep", "unclear_script", f"'{span.heard_text}' is unclear; best guess {top.name} only {top.score:.2f}")
            continue
        if span.all_common:
            # Round 1: "used" -> "Syed" on real speech. Ordinary English is never turned into a contact
            # (by rules OR by the LLM) unless it is exactly a KB name (handled above).
            item.set("keep", "common_words", f"'{span.heard_text}' is ordinary English")
            continue
        close = [c for c in span.candidates if c.score >= max(cfg.low, top.score - cfg.margin)]
        if top.score >= cfg.low and len(close) >= 2:
            clues = lexicons.clues_in(state["norm"], exclude=span.heard_text)
            areas = _areas_of_confident_businesses(state, span)
            expected = lexicons.expected_types(state["norm"])
            scored = []
            rest = _without_span(state, span)
            for c in close:
                score, why = lexicons.clue_score(get_by_id(c.entity_id), clues, rest)
                entity_c = get_by_id(c.entity_id)
                if expected and entity_c.type != "place" and lexicons.fits_type(entity_c, expected):
                    score, why = score + 3, why + [f"'{expected[0][1]}' fits {entity_c.name}"]
                if get_by_id(c.entity_id).name in areas:  # "Kakatiya Kitchen in Maghapur": the kitchen IS in Madhapur
                    score, why = score + 3, why + [f"{areas[get_by_id(c.entity_id).name]} is in {get_by_id(c.entity_id).name}"]
                scored.append(((score, why), c))
            best = max(s for (s, _), _ in scored)
            winners = [(w, c) for (s, w), c in scored if s == best]
            if best > 0 and len(winners) == 1:
                why, winner = winners[0]
                item.set("resolve", "tiebreak", f"{len(close)} close candidates; " + "; ".join(why),
                         winner.entity_id, winner.score)
            elif all(get_by_id(c.entity_id).type == "place" for c in close):
                # Two places that sound alike, no clue: a judgement call, not worth interrupting the user.
                item.set("llm", "llm", "close places, no clue: asking the LLM")
            elif top.score >= cfg.high:
                item.set("clarify", "close_call", f"'{span.heard_text}' fits " + " and ".join(c.name for c in close)
                         + " almost equally, and nothing in the sentence separates them",
                         clarify_ids=[c.entity_id for c in close])
            else:
                item.set("llm", "llm", "close, middling candidates: asking the LLM")
        elif top.score >= cfg.high:
            item.set("resolve", "high", f"sounds like {top.name} ({top.score:.2f}), clear lead of {span.margin:.2f}",
                     top.entity_id)
        elif top.score >= cfg.low:
            if span.all_common:
                item.set("keep", "common_words", f"'{span.heard_text}' is ordinary English; {top.name} only {top.score:.2f}")
            else:
                item.set("llm", "llm", f"unsure ({top.score:.2f}): asking the LLM")
        else:
            item.set("keep", "low", f"best candidate {top.name} only {top.score:.2f}")
    return {"items": state["items"]}


def needs_llm(state: State) -> str:
    """Conditional edge: only go to the LLM node if some span is still unsure."""
    return "llm_fallback" if any(i.status == "llm" for i in state["items"]) else "action"


# ---------------------------------------------------------------------------
# 6. llm_fallback: one small call for the unsure spans only
# ---------------------------------------------------------------------------
def llm_fallback_node(state: State) -> dict:
    """Example: "Call Aunt Johnny and ask if Matt's tuition is on": the LLM sees only this sentence and the
    3 candidates (Anthony, a priest; Manjunath, a cab driver; Anjani, the son's tuition teacher)."""
    pending = [i for i in state["items"] if i.status == "llm"]
    try:
        # A test passes its own fake client: then never read or write the real cache file.
        answers, cost, latency = ask_llm(state["transcript"], [i.span for i in pending], client=state.get("client"),
                                         use_cache=state.get("client") is None)
    except Exception as err:  # noqa: BLE001 (network or API trouble: be safe, keep as heard)
        for item in pending:
            item.set("keep", "llm_error", f"LLM unavailable ({type(err).__name__}): kept as heard")
        return {"items": state["items"]}
    by_phrase = {a["phrase"]: a for a in answers}
    for idx, item in enumerate(pending):
        answer = by_phrase.get(idx, {"choice": "keep", "reason": "no answer"})
        valid = {c.entity_id: c for c in item.span.candidates}
        if answer["choice"] in valid:
            item.set("resolve", "llm", f"LLM: {answer['reason']}", answer["choice"], valid[answer["choice"]].score)
        elif answer["choice"] == "clarify" and _is_action_target(state, item.span):
            item.set("clarify", "llm", f"LLM: {answer['reason']}", clarify_ids=list(valid)[:2])
        else:
            item.set("keep", "llm", f"LLM: {answer['reason']}")
    return {"items": state["items"], "used_llm": True, "cost_usd": state["cost_usd"] + cost,
            "llm_latency_ms": state["llm_latency_ms"] + latency}


# ---------------------------------------------------------------------------
# 7. action: the Remind, by rules
# ---------------------------------------------------------------------------
def _raw_time_text(transcript: str) -> str | None:
    """The time words as heard, e.g. "tomorrow at 10 a.m." (longest run of time-ish tokens)."""
    pattern = (r"\b(?:(?:at|by|on|before|after|this|next)\s+)?(?:\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?|"
               r"tomorrow|today|tonight|morning|evening|afternoon|night|monday|tuesday|wednesday|thursday|friday|"
               r"saturday|sunday|kal|subah|shaam|baje)(?:\s+(?:at\s+)?(?:\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?|"
               r"tomorrow|morning|evening|night|afternoon|baje|saat|subah|shaam))*")
    runs = [m.group().strip() for m in re.finditer(pattern, transcript, flags=re.IGNORECASE) if m.group().strip()]
    return max(runs, key=len) if runs else None


def action_node(state: State) -> dict:
    """Example: "Remind me to meet Gopikrishnan near Habsiguda at 7 PM" ->
    Remind(target=Gopikrishnan, place=Habsiguda, time=19:00). Clarify -> no action until the user answers."""
    items = state["items"]
    words = set(state["norm"].split())
    if any(i.status == "clarify" for i in items):
        return {"action": ActionDecision(type="none", raw_time_text=_raw_time_text(state["transcript"]))}
    if state["direction"] == "incoming":
        latin = transliterate(state["transcript"]) if has_indic(state["transcript"]) else state["transcript"]
        wanted = bool(words & TIME_WORDS) or normalise_time(latin) is not None
    else:
        wanted = bool(words & INTENT_WORDS)
    resolved = [get_by_id(i.entity_id) for i in sorted(items, key=lambda i: i.span.start) if i.status == "resolve"]
    people_or_shops = [e for e in resolved if e.type != "place"]
    places = [e for e in resolved if e.type == "place"]
    caller = state.get("caller_contact_id")
    businesses = [e for e in resolved if e.type == "business"]
    if state["direction"] == "incoming" and caller:
        target = caller
    elif businesses and words & {"order", "book"}:  # "Order Amma's tablets from the usual pharmacy"
        target = businesses[0].id
    elif people_or_shops:
        target = people_or_shops[0].id
    elif places and wanted:
        target = places[-1].id  # "book a cab to the airport": the destination
    else:
        target = None
    place = next((p.id for p in places if p.id != target), None)
    if not wanted:
        return {"action": ActionDecision(type="none")}
    latin = transliterate(state["transcript"]) if has_indic(state["transcript"]) else state["transcript"]
    return {"action": ActionDecision(type="remind", target_entity_id=target, place_entity_id=place,
                                     time=normalise_time(latin), raw_time_text=_raw_time_text(latin))}


# ---------------------------------------------------------------------------
# 8. assemble: the final Decision
# ---------------------------------------------------------------------------
def assemble_node(state: State) -> dict:
    """Builds the Decision: corrected transcript, entities with reasons, behaviour, candidates, cost, time."""
    items = sorted(state["items"], key=lambda i: i.span.start)
    text = state["transcript"]
    for item in reversed(items):  # replace right-to-left so earlier offsets stay valid
        if item.status == "resolve" and item.span.kind == "name":
            written = _written_form(item, text)
            end = _absorb_rest_of_name(item, text, written)
            if written and (written != item.span.heard_text or end != item.span.end):
                text = text[:item.span.start] + written + text[end:]
    if has_indic(text):  # Round 1: a Devanagari/Telugu transcript is given back in Latin letters
        text = transliterate(text)
    entities = [EntityDecision(heard_text=i.span.heard_text, resolved_entity_id=i.entity_id if i.status == "resolve" else None,
                               confidence=i.confidence, reason=f"{i.status}: {i.reason}")
                for i in items if i.status != "undecided" and (i.status != "keep" or i.span.candidates[0].score >= state["config"].low)]
    if any(i.status == "clarify" for i in items):
        behaviour = "clarify"
    elif any(i.status == "resolve" and i.how in NEEDS_CONTEXT for i in items):
        behaviour = "resolve"
    elif any(i.status == "resolve" for i in items):
        behaviour = "correct"
    else:
        behaviour = "keep"
    clarify_ids = list(dict.fromkeys(cid for i in items if i.status == "clarify" for cid in i.clarify_ids))
    latency = (time.perf_counter() - state["started"]) * 1000 + state["llm_latency_ms"]
    decision = Decision(
        clip_id=state.get("clip_id", "live"), system_name="pehchaan", heard_transcript=state["transcript"],
        output_transcript=text, behaviour=behaviour, entities=entities, clarify_candidates=clarify_ids,
        action=state["action"], used_llm=state["used_llm"], latency_ms=round(latency, 1),
        cost_usd=round(state["cost_usd"], 6),
    )
    return {"decision": decision}


def _written_form(item: Item, text: str) -> str:
    """What to write for a resolved name. The CANONICAL spelling ("Chikkanna", not the alias "Chikkana"),
    except a short form the speaker used on purpose ("Harshil", "Selvan") keeps its short form.
    An honorific already said just before ("Doctor ...") is not repeated."""
    entity = get_by_id(item.entity_id)
    form = next((c.form for c in item.span.candidates if c.entity_id == item.entity_id), "") or entity.name
    canonical_words = entity.name.split()
    has_title = canonical_words[0].rstrip(".").lower() in HONORIFIC_WORDS
    bare = canonical_words[1:] if has_title else canonical_words
    same_name = indian_phonetic_key(form) == indian_phonetic_key(" ".join(bare))  # "Sharmaji" == "Sharma Ji"
    if len(form.split()) < len(bare) and not same_name and not _next_word_completes(item, text, entity):
        written = form  # a short form the speaker chose ("Harshil", "Selvan"): keep it, correctly spelled
    else:
        before = normalise(text[:item.span.start]).split()
        said_title = bool(before) and before[-1] in HONORIFIC_WORDS
        written = " ".join(bare) if has_title and said_title else entity.name
    if not has_indic(item.span.heard_text) and normalise(written) == normalise(item.span.heard_text):
        return item.span.heard_text  # already right: leave the text exactly as heard
    return written


def _next_word_completes(item: Item, text: str, entity) -> bool:
    """Is the word right after the span the rest of this name? ("जिग्नेश" + "शाह" = Jignesh + Shah)"""
    nxt = re.match(r"\s*([\w\u0900-\u097F\u0C00-\u0C7F]+)", text[item.span.end:])
    return bool(nxt) and indian_phonetic_key(nxt.group(1)) == indian_phonetic_key(entity.name.split()[-1])


def _absorb_rest_of_name(item: Item, text: str, written: str) -> int:
    """End offset to replace: extends over the next word if it is the rest of the written full name."""
    entity = get_by_id(item.entity_id)
    if written == entity.name and _next_word_completes(item, text, entity):
        return item.span.end + re.match(r"\s*[\w\u0900-\u097F\u0C00-\u0C7F]+", text[item.span.end:]).end()
    return item.span.end


def build_graph():
    """Wire the nodes together. The only branch: go to the LLM node only if needed."""
    g = StateGraph(State)
    for name, fn in [("preferences", preferences_node), ("candidates", candidates_node),
                     ("references", references_node), ("context_check", context_check_node),
                     ("route", route_node), ("llm_fallback", llm_fallback_node),
                     ("action", action_node), ("assemble", assemble_node)]:
        g.add_node(name, fn)
    g.add_edge(START, "preferences")
    g.add_edge("preferences", "candidates")
    g.add_edge("candidates", "references")
    g.add_edge("references", "context_check")
    g.add_edge("context_check", "route")
    g.add_conditional_edges("route", needs_llm, {"llm_fallback": "llm_fallback", "action": "action"})
    g.add_edge("llm_fallback", "action")
    g.add_edge("action", "assemble")
    g.add_edge("assemble", END)
    return g.compile()
