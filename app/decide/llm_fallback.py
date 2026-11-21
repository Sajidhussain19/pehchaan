"""
app/decide/llm_fallback.py — the ONE small LLM call, used only when the rules are unsure.

WHAT: ask_llm(sentence, spans) sends gpt-4o-mini ONLY: the sentence, each unsure span's heard text,
      and its top-3 candidates (name, type, relation/roles/notes). It must answer, per span, with one
      candidate id, "keep" (probably not any of them) or "clarify" (two fit equally), through a strict
      JSON schema. Answers are cached by the exact prompt (data/results/pehchaan_llm_cache.json), so
      re-running costs nothing, while the original latency and cost are still reported honestly.
WHY:  Rules handle the clear cases fast and free. A middling score (e.g. "Aunt Johnny" ~ "Anjani"
      0.7) needs judgement in context. A tiny prompt is much cheaper than baseline (c)'s
      whole-phone-book prompt, and it can only choose among the candidates we give it.
"""

import hashlib
import json
import threading
import time

from app.decide.config import DEFAULT
from app.kb.loader import get_by_id
from app.stt.baseline import RESULTS_DIR
from app.stt.transcribe import get_client

CACHE_PATH = RESULTS_DIR / "pehchaan_llm_cache.json"
PRICE_INPUT, PRICE_OUTPUT = 0.15 / 1_000_000, 0.60 / 1_000_000  # gpt-4o-mini, US$ per token
_lock = threading.Lock()

INSTRUCTIONS = """You help a voice assistant in Hyderabad, India. Speech-to-text often mishears Indian names
("Anjani" -> "Aunt Johnny", "Abids" -> "a bit"). For each heard phrase below you get up to 3 candidates
from the user's own contacts, places and businesses. Decide, using the whole sentence:
- the candidate's id, if the phrase clearly refers to that candidate (sound + the sentence fits who they are)
- "keep", if the phrase is probably NOT any of them (ordinary words, or a different person/place)
- "clarify", if two candidates fit equally well
Be conservative: a wrong person is worse than asking or keeping.
Pick a candidate ONLY if the sentence clearly refers to that exact contact, place or business. A similar sound is
NOT enough. Answer "keep" when the phrase is part of a name that is not in the list (an unknown restaurant, shop,
person or town), when the candidate's type does not fit (a restaurant name is not a city), or when you are unsure.
A family word (Amma, Nanna, Akka, Anna, Bhaiya...) means that family member HIMSELF/HERSELF, never someone
whose relation merely mentions them (e.g. "Nanna's cardiologist" is NOT "Nanna"). Ordinary words are "keep"."""


def _candidate_line(c) -> str:
    e = get_by_id(c.entity_id)
    ctx = e.context
    if e.type == "person":
        detail = f"person; {ctx['relation']}; roles: {', '.join(ctx.get('roles', []))}; {ctx.get('notes', '')}"
    elif e.type == "business":
        detail = f"business; {ctx['category']} in {ctx['area']}"
    else:
        detail = f"place in {ctx['city']}"
    return f"  - {e.id}: {e.name} ({detail.strip('; ')}) [match score {c.score:.2f}]"


def build_prompt(sentence: str, spans: list) -> str:
    lines = [f"Sentence: {sentence}", ""]
    for i, span in enumerate(spans):
        lines.append(f"Phrase {i}: \"{span.heard_text}\"")
        lines += [_candidate_line(c) for c in span.candidates]
    return "\n".join(lines)


def _schema(spans: list) -> dict:
    choices = sorted({c.entity_id for s in spans for c in s.candidates} | {"keep", "clarify"})
    return {"type": "object", "additionalProperties": False, "required": ["decisions"],
            "properties": {"decisions": {"type": "array", "items": {
                "type": "object", "additionalProperties": False, "required": ["phrase", "choice", "reason"],
                "properties": {"phrase": {"type": "integer"}, "choice": {"type": "string", "enum": choices},
                               "reason": {"type": "string"}}}}}}


def _load_cache() -> dict:
    return json.loads(CACHE_PATH.read_text(encoding="utf-8")) if CACHE_PATH.exists() else {}


def ask_llm(sentence: str, spans: list, client=None, use_cache: bool = True) -> tuple[list[dict], float, float]:
    """Returns ([{phrase, choice, reason}], cost_usd, latency_ms). One call for all unsure spans of a clip."""
    prompt = build_prompt(sentence, spans)
    # The key covers EVERYTHING that shapes the answer: instructions, model and prompt. (Round 2 bug fix:
    # it used to be the prompt only, so an instruction change silently reused old answers.)
    key = hashlib.sha256(f"{DEFAULT.llm_model}\n{INSTRUCTIONS}\n{prompt}".encode("utf-8")).hexdigest()
    if use_cache:
        with _lock:
            cached = _load_cache().get(key)
        if cached:
            return cached["decisions"], cached["cost_usd"], cached["latency_ms"]

    client = client or get_client()
    start = time.perf_counter()
    response = client.chat.completions.create(
        model=DEFAULT.llm_model, temperature=0,
        messages=[{"role": "system", "content": INSTRUCTIONS}, {"role": "user", "content": prompt}],
        response_format={"type": "json_schema",
                         "json_schema": {"name": "span_choices", "strict": True, "schema": _schema(spans)}},
    )
    latency_ms = (time.perf_counter() - start) * 1000
    decisions = json.loads(response.choices[0].message.content)["decisions"]
    cost = response.usage.prompt_tokens * PRICE_INPUT + response.usage.completion_tokens * PRICE_OUTPUT

    if use_cache:
        with _lock:
            cache = _load_cache()
            cache[key] = {"decisions": decisions, "cost_usd": cost, "latency_ms": latency_ms}
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            CACHE_PATH.write_text(json.dumps(cache, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return decisions, cost, latency_ms
