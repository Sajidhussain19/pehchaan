"""
app/eval/decision.py — the common decision format every resolver system outputs, per clip.

WHAT: `Decision` = what a system concluded about one clip:
        - what it heard (input transcript) and its output transcript
        - its behaviour: correct / keep / resolve / clarify
        - each entity: heard text -> resolved KB id (or none) -> confidence -> reason
        - who to ask about (clarify candidates)
        - the action: a Remind (target person/business, place, "HH:MM" time) or none
        - whether an LLM was used, latency, and cost
WHY:  Baseline (c) (one GPT-4o-mini call) and Pehchaan (Modules 6-8) both output this, so the
      metrics treat them identically. It also enforces "never hide what was heard": every
      resolved entity carries the heard text, a confidence and a reason.

Behaviour meanings (same as the test set):
    correct -> names were linked to KB entities (respelled if needed)
    keep    -> nothing linked; the transcript is left as heard
    resolve -> look-alikes or a personal reference ("my doctor") were resolved using context
    clarify -> the system asks the user, listing candidates; no action is taken yet
"""

from typing import Literal

from pydantic import BaseModel, Field

from app.kb.loader import get_by_id

Behaviour = Literal["correct", "keep", "resolve", "clarify"]


class EntityDecision(BaseModel):
    """One heard name/reference and what the system made of it."""

    heard_text: str  # exactly what was in the transcript, e.g. "cook at Polly" or "my doctor"
    resolved_entity_id: str | None  # the KB id it means, or None (kept as heard)
    confidence: float = Field(ge=0, le=1)
    reason: str  # short human-readable why, e.g. "clue: tooth -> dentist"


class ActionDecision(BaseModel):
    """The one real action in scope: Remind. "none" when nothing should be done (yet)."""

    type: Literal["remind", "none"]
    target_entity_id: str | None = None  # who/what the reminder is about
    place_entity_id: str | None = None  # where, if a KB place was mentioned
    time: str | None = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")  # "HH:MM" or None
    raw_time_text: str | None = None  # the time words as heard, e.g. "tomorrow at 10 AM"


class Decision(BaseModel):
    """Everything one system decided for one clip."""

    clip_id: str
    system_name: str  # e.g. "llm_baseline", "pehchaan"
    heard_transcript: str  # the input: baseline (a) speech-to-text output
    output_transcript: str  # the transcript after the system's corrections
    behaviour: Behaviour
    entities: list[EntityDecision] = []
    clarify_candidates: list[str] = []  # KB ids; only meaningful when behaviour == "clarify"
    action: ActionDecision
    used_llm: bool
    latency_ms: float = Field(ge=0)
    cost_usd: float = Field(ge=0)

    def all_ids(self) -> list[str]:
        """Every KB id this decision mentions (entities, candidates, action)."""
        ids = [e.resolved_entity_id for e in self.entities if e.resolved_entity_id]
        ids += self.clarify_candidates
        ids += [i for i in (self.action.target_entity_id, self.action.place_entity_id) if i]
        return ids

    def invalid_ids(self) -> list[str]:
        """Ids that do NOT exist in the KB. We never crash on them: the metrics count any
        invalid id as a wrong target (inventing an entity is the worst kind of mistake)."""
        return [i for i in self.all_ids() if get_by_id(i) is None]
