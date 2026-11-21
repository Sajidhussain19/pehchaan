"""
app/testset/models.py — Pydantic models for one test sentence and its ground truth.

WHAT: Describes a test sentence: its text, category, call direction, which entities it mentions
      (with the correct KB id), what Pehchaan SHOULD do (correct / keep / resolve / clarify), and
      the action the assistant should take (call / book / remind / message / none).
WHY:  The test set is the "answer key" for the whole project. These models reject a malformed
      entry (a typo in a category, a missing field, a clarify without candidates) at load time.
      Checks that need the knowledge base live in validate.py.
"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

Category = Literal["in_kb", "out_of_kb", "control", "ambiguous", "context_mismatch"]

# What Pehchaan is expected to do with the sentence:
#   correct -> the names are in the KB: fix any mis-hearing to the canonical spelling
#   keep    -> leave the text alone and link nothing (unknown names, or no names at all)
#   resolve -> near-identical candidates exist, but context picks the right one
#   clarify -> the system cannot safely decide, so it should ASK the user
Behaviour = Literal["correct", "keep", "resolve", "clarify"]


class EntitySpan(BaseModel):
    """One name mentioned in the sentence."""

    model_config = {"extra": "forbid"}

    surface: str = Field(min_length=1)  # the exact text as it appears in the sentence
    entity_id: str | None  # the correct KB id, or None if it must NOT be linked to the KB
    type: Literal["person", "place", "business"]


class ExpectedAction(BaseModel):
    """The structured action the assistant should produce (scored in Module 5 / built in Module 9)."""

    model_config = {"extra": "forbid"}

    type: Literal["call", "book", "remind", "message", "none"]
    # Who/what the action is about. None when there is no KB target: unknown names,
    # or a "clarify" case where we must ask before acting.
    target_entity_id: str | None = None
    time: str | None = None  # the time phrase as spoken, e.g. "tomorrow at 10 AM"


class Sentence(BaseModel):
    """One test sentence plus everything we expect Pehchaan to get right about it."""

    model_config = {"extra": "forbid"}

    id: str = Field(pattern=r"^s\d{3}$")  # "s001"
    split: Literal["dev", "test"]
    text: str = Field(min_length=1)
    category: Category
    direction: Literal["incoming", "outgoing"]
    # For an incoming call from a saved contact's number: that contact's id. Otherwise None.
    caller_contact_id: str | None = None
    entities: list[EntitySpan] = []
    expected_behaviour: Behaviour
    candidate_ids: list[str] = []  # only for "clarify": the KB ids we should ask about
    expected_action: ExpectedAction

    @model_validator(mode="after")
    def check_internal_consistency(self):
        # Every entity surface must literally appear in the text. Later modules
        # score span detection on exact text, so a mismatch would corrupt the scores.
        for span in self.entities:
            if span.surface not in self.text:
                raise ValueError(f"{self.id}: surface {span.surface!r} not found in text")

        # Outgoing commands have no caller. Only incoming calls can come from a contact.
        if self.direction == "outgoing" and self.caller_contact_id is not None:
            raise ValueError(f"{self.id}: outgoing sentence cannot have a caller_contact_id")

        # Candidates are only meaningful when the answer is "ask the user".
        if self.expected_behaviour == "clarify" and not self.candidate_ids:
            raise ValueError(f"{self.id}: clarify needs at least one candidate id")
        if self.expected_behaviour != "clarify" and self.candidate_ids:
            raise ValueError(f"{self.id}: candidate_ids are only allowed for clarify")

        # When we must ask first, the action cannot already have a target.
        if self.expected_behaviour == "clarify" and self.expected_action.target_entity_id is not None:
            raise ValueError(f"{self.id}: a clarify sentence cannot have an action target yet")
        return self
