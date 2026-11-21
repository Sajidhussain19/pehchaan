"""
app/stt/hints.py — builds the "name hints" prompt for baseline (b).

WHAT: `build_hint_prompt(model)` turns the knowledge base into a short vocabulary list, e.g.
      "Names and places that may appear: Dr. Venkataramana, Kukatpally, ...", and sends it as the
      transcription prompt. If the whole KB doesn't fit within the model's prompt budget, it
      includes as many names as fit, in priority order, and records what was left out:
        1. contacts (the user's own people: most valuable and most often misheard)
        2. Hyderabad / Secunderabad places (where our user lives)
        3. local businesses
        4. other Indian places
WHY:  Baseline (b) is the obvious "cheap fix": tell the speech model which names to expect.
      We make it as strong as we fairly can (every name that fits), so beating it means something.
      The budget also shows why hints don't scale: a real phone book plus places quickly outgrows
      what a prompt can hold, and a prompt can't decide WHICH "doctor" you meant.
"""

import math
from dataclasses import dataclass, field

from app.kb.loader import get_by_type

# Prompt budgets in (estimated) tokens.
# - whisper-1: OpenAI documents that only the last 224 tokens of the prompt are used.
# - gpt-4o(-mini)-transcribe: no small fixed limit is documented. In our own test (Module 4),
#   a ~5,300-token prompt worked and a ~21,000-token prompt failed with "instructions + audio is
#   too large". The prompt shares the model's context with the audio, so we stay at 4,000.
PROMPT_TOKEN_BUDGET = {
    "whisper-1": 224,
    "gpt-4o-mini-transcribe": 4000,
    "gpt-4o-transcribe": 4000,
}
HYDERABAD_CITIES = {"Hyderabad", "Secunderabad"}
PREFIX = "Names and places that may appear: "


def estimate_tokens(text: str) -> int:
    """Rough token count: English text averages about 4 characters per token.
    Good enough for a budget, and it needs no extra tokenizer library."""
    return math.ceil(len(text) / 4)


@dataclass
class HintPrompt:
    """The prompt text plus a record of what made it in, so results can report it honestly."""

    text: str
    budget_tokens: int
    estimated_tokens: int
    included_ids: list[str] = field(default_factory=list)
    excluded_ids: list[str] = field(default_factory=list)

    def summary(self) -> dict:
        """Small dict stored in the results file (we don't store every id, just the counts)."""
        return {
            "budget_tokens": self.budget_tokens,
            "estimated_tokens": self.estimated_tokens,
            "included": len(self.included_ids),
            "excluded": len(self.excluded_ids),
        }


def prioritised_entities() -> list:
    """All KB entities in priority order: contacts, Hyderabad places, businesses, other places."""
    places = get_by_type("place")
    local = [p for p in places if p.context["city"] in HYDERABAD_CITIES]
    other = [p for p in places if p.context["city"] not in HYDERABAD_CITIES]
    return [*get_by_type("person"), *local, *get_by_type("business"), *other]


def build_hint_prompt(model: str | None = None, budget_tokens: int | None = None) -> HintPrompt:
    """Greedy fill: add names in priority order while the prompt stays within the budget."""
    if budget_tokens is None:
        budget_tokens = PROMPT_TOKEN_BUDGET.get(model, 224)  # unknown model: be conservative

    names: list[str] = []
    included, excluded = [], []
    for entity in prioritised_entities():
        candidate = PREFIX + ", ".join([*names, entity.name]) + "."
        if estimate_tokens(candidate) <= budget_tokens:
            names.append(entity.name)
            included.append(entity.id)
        else:
            # Keep going: a later, shorter name might still fit. Record what was left out.
            excluded.append(entity.id)

    text = PREFIX + ", ".join(names) + "." if names else ""
    return HintPrompt(text=text, budget_tokens=budget_tokens, estimated_tokens=estimate_tokens(text),
                      included_ids=included, excluded_ids=excluded)
