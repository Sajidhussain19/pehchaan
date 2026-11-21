"""
app/api/flow.py — the end-to-end flow behind the API, as plain Python (no HTTP here).

WHAT: process()  transcript -> Pehchaan decision -> a stored reminder, or a pending clarify question.
                 Optionally also runs baseline (c) on the SAME transcript, for a side-by-side view.
      answer()   the user's answer to a pending question -> the reminder. remember="always" also saves a
                 preference for that contact book; "this_time" saves nothing.
      Both return plain dicts that the API sends as JSON.
WHY:  Keeping the logic out of the web layer makes it easy to test and to explain:
      routes.py only checks inputs and calls these two functions.

How an answer becomes a reminder: we re-run the SAME pipeline with the answer supplied as a preference
("my doctor" -> Dr. Subramanian). That way the reminder's time and place come from exactly the same rules
as an automatic one. For "this_time" the preference is only passed in for this one run and never saved.
"""

import time
from datetime import datetime

from app.baselines import llm_resolver
from app.decide.pehchaan import trace
from app.eval.decision import Decision
from app.kb.loader import get_by_id, load_preferences, use_book
from app.kb.models import Preference
from app.match.phonetic import normalise
from app.store import pending as pending_store
from app.store import preferences as preference_store
from app.store import reminders as reminder_store
from app.store.reminders import Reminder


class FlowError(ValueError):
    """A request that can't be done (unknown pending id, answer not among the candidates...)."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def role_of(entity) -> str | None:
    """A short human label: "dentist", "family doctor", "restaurant", "place"."""
    if entity is None:
        return None
    ctx = entity.context
    if entity.type == "person":
        return ctx.get("relation") or ", ".join(ctx.get("roles", [])) or None
    if entity.type == "business":
        return ctx.get("category")
    return "place"


def marked_spans(decision: Decision) -> list[dict]:
    """Every entity with WHERE it is, so the UI can highlight it in both transcripts.

    heard_start/heard_end: character positions in the heard transcript; output_start/output_end: in the
    corrected transcript (None when the text can't be found, e.g. after transliteration).
    """
    out, heard_pos, out_pos = [], 0, 0
    for e in decision.entities:
        entity = get_by_id(e.resolved_entity_id) if e.resolved_entity_id else None
        hs = decision.heard_transcript.find(e.heard_text, heard_pos)
        written = next((w for w in ([entity.name, *entity.aliases] if entity else []) + [e.heard_text]
                        if decision.output_transcript.find(w, out_pos) >= 0), None)
        os_ = decision.output_transcript.find(written, out_pos) if written else -1
        out.append({"heard_text": e.heard_text, "resolved_entity_id": e.resolved_entity_id,
                    "resolved_name": entity.name if entity else None, "role": role_of(entity),
                    "confidence": e.confidence, "reason": e.reason,
                    "heard_start": hs if hs >= 0 else None, "heard_end": hs + len(e.heard_text) if hs >= 0 else None,
                    "output_start": os_ if os_ >= 0 else None,
                    "output_end": os_ + len(written) if os_ >= 0 else None})
        heard_pos = hs + len(e.heard_text) if hs >= 0 else heard_pos
        out_pos = os_ + len(written) if os_ >= 0 else out_pos
    return out


def _reminder_from(decision: Decision, book: str, resolution: str) -> Reminder:
    """Build the stored reminder from a 'remind' decision (names/roles looked up in the same book)."""
    a = decision.action
    target = get_by_id(a.target_entity_id) if a.target_entity_id else None
    place = get_by_id(a.place_entity_id) if a.place_entity_id else None
    return Reminder(contact_book=book, heard_transcript=decision.heard_transcript,
                    output_transcript=decision.output_transcript, target_entity_id=a.target_entity_id,
                    target_name=target.name if target else None, target_role=role_of(target),
                    place_entity_id=a.place_entity_id, place_name=place.name if place else None,
                    time=a.time, raw_time_text=a.raw_time_text,
                    entities=[e.model_dump() for e in decision.entities], resolution=resolution)


def _first_question(state: dict) -> dict | None:
    """The span we must ask about: the phrase, why, and the candidates with name + role + reason."""
    item = next((i for i in state["items"] if i.status == "clarify"), None)
    if item is None:
        return None
    ids = item.clarify_ids or state["decision"].clarify_candidates
    candidates = []
    for eid in ids:
        e = get_by_id(eid)
        if e is not None:
            notes = e.context.get("notes") or ""
            candidates.append({"entity_id": eid, "name": e.name, "role": role_of(e),
                               "reason": f"{role_of(e)}" + (f"; {notes}" if notes else "")})
    return {"phrase": normalise(item.span.heard_text), "heard_text": item.span.heard_text, "reason": item.reason,
            "candidates": candidates}


def _decide_and_store(transcript: str, book: str, direction: str, caller: str | None, client,
                      preferences=None, resolution_if_resolved: str | None = None) -> dict:
    """Run Pehchaan, then store a reminder or a pending question. Returns the result plus timings."""
    t0 = time.perf_counter()
    state = trace(transcript, direction, caller, preferences=preferences, client=client, book=book)
    decision: Decision = state["decision"]
    pehchaan_ms = (time.perf_counter() - t0) * 1000
    result = {"decision": decision.model_dump(), "reminder": None, "pending": None, "pehchaan_ms": round(pehchaan_ms, 1)}
    with use_book(book):  # names and roles come from the same contact book the decision used
        result["spans"] = marked_spans(decision)
        if decision.behaviour == "clarify":
            q = _first_question(state)
            if q:  # store the question; nothing is done until the user answers
                item = pending_store.create(book, transcript, direction, caller, q["phrase"], q["reason"],
                                            q["candidates"])
                result["pending"] = {**item, "heard_text": q["heard_text"],
                                     "buttons": [{"label": f"Use {c['name']} this time", "entity_id": c["entity_id"],
                                                  "remember": "this_time"} for c in q["candidates"]]
                                     + [{"label": f"Always use {c['name']} for '{q['phrase']}'",
                                         "entity_id": c["entity_id"], "remember": "always"} for c in q["candidates"]]}
        elif decision.action.type == "remind":
            if resolution_if_resolved is None:
                learned = any(i.status == "resolve" and i.how == "preference" for i in state["items"])
                resolution = "preference" if learned else "auto"
            else:
                resolution = resolution_if_resolved
            result["reminder"] = reminder_store.create(_reminder_from(decision, book, resolution)).model_dump()
    result["store_ms"] = round((time.perf_counter() - t0) * 1000 - pehchaan_ms, 1)
    return result


def process(transcript: str, book: str = "default", direction: str = "outgoing", caller: str | None = None,
            client=None, compare: bool = False) -> dict:
    """Pehchaan on one transcript -> reminder or pending question (+ baseline (c) side by side if compare)."""
    result = _decide_and_store(transcript, book, direction, caller, client)
    result["baseline"], result["baseline_ms"], result["baseline_cost_usd"] = None, None, None
    result["baseline_error"] = None
    if compare:
        # Baseline (c) gets exactly the same transcript, caller info and contact book. It only DECIDES:
        # nothing it says is stored, so the comparison can't change the user's reminders.
        t0 = time.perf_counter()
        try:
            with use_book(book):
                base = llm_resolver.resolve("live", transcript, direction, caller, client=client)
        except Exception as err:  # noqa: BLE001  If OpenAI is down, Pehchaan's answer must still come back.
            result["baseline_error"] = f"Strong AI unavailable ({type(err).__name__}) — comparison skipped"
            return result
        result["baseline"] = base.model_dump()
        result["baseline_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        result["baseline_cost_usd"] = base.cost_usd
    return result


def answer(pending_id: str, entity_id: str, remember: str, client=None) -> dict:
    """The user picked `entity_id` for a pending question. Creates the reminder; 'always' also learns."""
    item = pending_store.get(pending_id)
    if item is None:
        raise FlowError(f"no pending question {pending_id!r}", status=404)
    if item["status"] != "open":
        raise FlowError("this question was already answered", status=409)
    if entity_id not in {c["entity_id"] for c in item["candidates"]}:
        raise FlowError(f"{entity_id!r} is not one of the offered candidates", status=400)
    if remember not in ("this_time", "always"):
        raise FlowError("remember must be 'this_time' or 'always'", status=400)

    book = item["contact_book"]
    saved = None
    if remember == "always":  # consent given: save it for this book, so next time no question is asked
        saved = preference_store.save(book, item["phrase"], entity_id).model_dump(mode="json")
    with use_book(book):
        prefs = load_preferences()
    # For this one run, the answer acts like a preference (also for "this_time", where it is NOT saved).
    prefs = [*prefs, Preference(phrase_pattern=item["phrase"], entity_id=entity_id, created_at=datetime.now())]
    resolution = "clarified_always" if remember == "always" else "clarified_this_time"
    result = _decide_and_store(item["heard_transcript"], book, item["direction"], item["caller_contact_id"], client,
                               preferences=prefs, resolution_if_resolved=resolution)
    pending_store.mark_answered(pending_id, result["reminder"]["id"] if result["reminder"] else None)
    result["saved_preference"] = saved
    return result
