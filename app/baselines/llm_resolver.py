"""
app/baselines/llm_resolver.py — baseline (c): the STRONG LLM baseline.

WHAT: For one clip it makes ONE gpt-4o-mini call. The call gets:
        - the raw baseline-(a) transcript (plain speech-to-text)
        - the call context (outgoing command, or incoming from a saved contact / unknown number)
        - the user's FULL personal context: every contact (aliases, relation, roles, default-for,
          family label, notes), every business (category, area, usual-for), every place
      It returns a `Decision` (app/eval/decision.py), the same format Pehchaan will produce.
      Structured output with a strict JSON schema forces every id to be a real KB id (or null).
WHY:  Judges will ask: "Is Pehchaan better than just giving one LLM your contacts?" This is that
      opponent, prompted as well as we can: the same rules Pehchaan follows (clue -> default -> ask,
      never invent, keep unknown names). If Pehchaan can't beat or tie it, we must say so.
"""

import json
import time

from app.config import settings
from app.eval.decision import ActionDecision, Decision, EntityDecision
from app.kb.loader import get_by_id, get_by_type, per_book_cache
from app.stt.transcribe import get_client

SYSTEM_NAME = "llm_baseline"

# gpt-4o-mini prices (US dollars per token), for cost estimates. Cached input = repeated prompt prefix.
PRICE_INPUT = 0.15 / 1_000_000
PRICE_CACHED_INPUT = 0.075 / 1_000_000
PRICE_OUTPUT = 0.60 / 1_000_000

INSTRUCTIONS = """You are the "personal ear" of a voice assistant for a user in Hyderabad, India.
You receive a speech-to-text transcript of a phone call or a spoken command, plus the user's personal
context (their contacts, the places they know, the businesses they use). Speech-to-text often mishears
Indian names ("Kukatpally" -> "cook at Polly", "Anjani" -> "Aunt Johnny"), and code-mixed Hindi/Telugu
speech may come back in Devanagari or Telugu script. Your job: work out WHO or WHAT the user means,
using ONLY the context below.

RULES
1. Find every person/place/business name AND every personal reference ("my doctor", "Amma", "my manager",
   "the usual pharmacy"). For each, give heard_text exactly as it appears in the transcript, the KB id it
   means (or null), a confidence from 0 to 1, and a short reason.
2. Use ONLY ids from the context. Never invent an entity. If a name is not in the context, keep it as
   heard with resolved_entity_id null. A name that merely sounds similar to a contact (one sound away,
   or a different surname, e.g. "Rohan" when the contact is "Rohit") is probably SOMEONE ELSE: do not
   link it (you may ask instead).
3. A name must fit the context. "Book a table at Raju Hotel" does not mean Dr. Raju (a doctor, not a
   restaurant). On an INCOMING call from an UNKNOWN number, a caller who says a contact's name
   ("I'm Raju from the bank") is a different person: do not link. A call from a SAVED contact's number
   tells you who is speaking.
4. Resolution order for personal references and look-alike names:
   a) a clue in the sentence wins ("my doctor, my tooth is paining" -> the dentist), even over a default;
   b) otherwise the user's default for that role ("default for: doctor");
   c) otherwise ASK (clarify), listing the candidates. Ask when two candidates fit equally well, e.g.
      near-identical names ("Harshit" vs "Harshil") with no clue, or "my colleague" with many colleagues.
   A family word ("Amma", "Nanna", "Akka") means the contact with that family label. "The usual X" means
   the business marked usual for X.
5. behaviour (one for the whole clip):
   - "correct": the clip names KB entities (fix their spelling if misheard), no look-alike/reference puzzle
   - "keep": nothing should be linked to the KB (unknown names, or no names at all)
   - "resolve": you resolved a personal reference or chose between look-alike contacts using context
   - "clarify": you cannot decide safely; list the candidate ids in clarify_candidates
6. output_transcript: the transcript with every resolved name written in its canonical spelling from the
   context (Latin script). Leave everything else as heard. Never insert names that were not spoken.
7. action: the only action is "remind".
   - Use type "remind" when the user asks to do something about someone/somewhere (call, book, message,
     tell, ask, order, remind, visit) or an incoming caller sets an appointment/meeting time.
     Plain information with no request is type "none".
   - target_entity_id: the KB person/business the action is about (for travel, e.g. "book a cab to X",
     the destination place). null if that person/business is not in the context.
   - place_entity_id: a KB place mentioned in the clip other than the target, else null.
   - time: 24-hour "HH:MM" only for a clear clock time ("10 AM" -> "10:00", "8 PM" -> "20:00",
     "shaam saat baje" -> "19:00"); null if there is no clock time or AM/PM is ambiguous ("at 5").
     raw_time_text: the time words as heard ("tomorrow at 10 AM"), or null.
   - When behaviour is "clarify": type "none", target null (we ask before acting).
"""


def _person_line(e) -> str:
    c = e.context
    parts = [e.id, e.name]
    if e.aliases:
        parts.append("aka " + ", ".join(e.aliases))
    parts.append(f"relation: {c['relation']}")
    if c.get("roles"):
        parts.append("roles: " + ", ".join(c["roles"]))
    if c.get("is_primary_for"):
        parts.append("DEFAULT for: " + ", ".join(c["is_primary_for"]))
    if c.get("family_label"):
        parts.append(f"family label: {c['family_label']}")
    if c.get("notes"):
        parts.append(f"notes: {c['notes']}")
    return " | ".join(parts)


def _business_line(e) -> str:
    c = e.context
    parts = [e.id, e.name]
    if e.aliases:
        parts.append("aka " + ", ".join(e.aliases))
    parts.append(f"{c['category']} in {c['area']}, {c['city']}")
    if c.get("is_usual"):
        parts.append(f"USUAL for: {c['usual_for']}")
    return " | ".join(parts)


def _place_line(e) -> str:
    c = e.context
    alias = f" | aka {', '.join(e.aliases)}" if e.aliases else ""
    return f"{e.id} | {e.name}{alias} | {c['kind']} in {c['city']}, {c['state']}"


@per_book_cache  # one cached copy per contact book (Module 9)
def context_text() -> str:
    """The user's whole personal context as compact text lines (identical for every call,
    which lets OpenAI's automatic prompt caching make repeat calls cheaper)."""
    return "\n".join([
        "CONTACTS (id | name | aliases | relation | roles | default for | family label | notes):",
        *(_person_line(e) for e in get_by_type("person")),
        "\nBUSINESSES (id | name | aliases | category and area | usual for):",
        *(_business_line(e) for e in get_by_type("business")),
        "\nPLACES (id | name | aliases | kind and city):",
        *(_place_line(e) for e in get_by_type("place")),
    ])


@per_book_cache  # one cached copy per contact book (Module 9)
def output_schema() -> dict:
    """Strict JSON schema for the answer. Every id field must be one of the real KB ids (an enum),
    so the model physically cannot output an invented id."""
    ids = [e.id for t in ("person", "place", "business") for e in get_by_type(t)]
    eid_or_null = {"anyOf": [{"$ref": "#/$defs/EntityId"}, {"type": "null"}]}
    str_or_null = {"type": ["string", "null"]}
    return {
        "type": "object", "additionalProperties": False,
        "required": ["output_transcript", "behaviour", "entities", "clarify_candidates", "action"],
        "properties": {
            "output_transcript": {"type": "string"},
            "behaviour": {"type": "string", "enum": ["correct", "keep", "resolve", "clarify"]},
            "entities": {"type": "array", "items": {
                "type": "object", "additionalProperties": False,
                "required": ["heard_text", "resolved_entity_id", "confidence", "reason"],
                "properties": {"heard_text": {"type": "string"}, "resolved_entity_id": eid_or_null,
                               "confidence": {"type": "number"}, "reason": {"type": "string"}},
            }},
            "clarify_candidates": {"type": "array", "items": {"$ref": "#/$defs/EntityId"}},
            "action": {
                "type": "object", "additionalProperties": False,
                "required": ["type", "target_entity_id", "place_entity_id", "time", "raw_time_text"],
                "properties": {"type": {"type": "string", "enum": ["remind", "none"]},
                               "target_entity_id": eid_or_null, "place_entity_id": eid_or_null,
                               "time": str_or_null, "raw_time_text": str_or_null},
            },
        },
        "$defs": {"EntityId": {"type": "string", "enum": ids}},
    }


def call_context(direction: str, caller_contact_id: str | None) -> str:
    """Plain-words description of who is talking. Pehchaan gets exactly the same information."""
    if direction == "outgoing":
        return "Outgoing: the user is speaking to their assistant."
    if caller_contact_id and (caller := get_by_id(caller_contact_id)):
        return f"Incoming call from a SAVED contact's number: {caller.id} ({caller.name})."
    return "Incoming call from an UNKNOWN number (not in contacts)."


def resolve(clip_id: str, transcript: str, direction: str = "outgoing", caller_contact_id: str | None = None,
            model: str | None = None, client=None) -> Decision:
    """One LLM call -> one Decision. `client` can be a fake in tests."""
    model = model or settings.chat_model
    client = client or get_client()
    messages = [
        # System message = instructions + the whole context: the same for every clip (cacheable prefix).
        {"role": "system", "content": INSTRUCTIONS + "\nUSER'S PERSONAL CONTEXT\n" + context_text()},
        {"role": "user", "content": f"Call context: {call_context(direction, caller_contact_id)}\n"
                                    f"Transcript: {transcript}"},
    ]
    start = time.perf_counter()
    response = client.chat.completions.create(
        model=model, messages=messages, temperature=0,  # temperature 0: as repeatable as possible
        response_format={"type": "json_schema",
                         "json_schema": {"name": "decision", "strict": True, "schema": output_schema()}},
    )
    latency_ms = (time.perf_counter() - start) * 1000
    data = json.loads(response.choices[0].message.content)

    # Cost from the token counts the API reports (cached prompt tokens are cheaper).
    usage = response.usage
    cached = getattr(getattr(usage, "prompt_tokens_details", None), "cached_tokens", 0) or 0
    cost = ((usage.prompt_tokens - cached) * PRICE_INPUT + cached * PRICE_CACHED_INPUT
            + usage.completion_tokens * PRICE_OUTPUT)

    # The schema can't express "HH:MM" strictly, so drop any malformed time instead of crashing.
    action = data["action"]
    try:
        parsed_action = ActionDecision(**action)
    except ValueError:
        parsed_action = ActionDecision(**{**action, "time": None})

    return Decision(
        clip_id=clip_id, system_name=SYSTEM_NAME, heard_transcript=transcript,
        output_transcript=data["output_transcript"], behaviour=data["behaviour"],
        entities=[EntityDecision(**{**e, "confidence": min(max(e["confidence"], 0.0), 1.0)})
                  for e in data["entities"]],
        clarify_candidates=data["clarify_candidates"], action=parsed_action,
        used_llm=True, latency_ms=round(latency_ms, 1), cost_usd=round(cost, 6),
    )


def estimate_cost_per_call() -> float:
    """Rough cost of one call before running: context + instructions in, ~250 tokens out."""
    prompt_tokens = (len(INSTRUCTIONS) + len(context_text())) / 4 + 60
    return prompt_tokens * PRICE_INPUT + 250 * PRICE_OUTPUT
