"""
app/testset/models.py — Pydantic models for one test sentence and its ground truth.

WHAT: Describes a test sentence: its text, category, call direction, which entities it mentions
      (with the correct KB id), what Pehchaan SHOULD do (correct / keep / resolve / clarify), and
      the action the assistant should take (call / book / remind / message / none).
WHY:  The test set is the "answer key" for the whole project. These models reject a malformed
      entry (a typo in a category, a missing field, a clarify without candidates) at load time.
      Checks that need the knowledge base live in validate.py.
      `RealSpeechClip` describes one real-speaker clip (data/realspeech/manifest.json).
"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

Category = Literal[
    "in_kb", "out_of_kb", "control", "ambiguous", "context_mismatch", "reference",
    # Added after the judge review:
    "unfamiliar_near_match",  # a name one sound away from a contact, but NOT a contact ("Rohan" vs "Rohit")
    "stale_default",  # a clue in the sentence beats the user's default ("my doctor about my eye drops")
]

# Why a personal reference ("my doctor", "Amma") points to a particular entity:
#   clue         -> a word in the sentence picks the role ("tooth" -> the dentist)
#   primary      -> the user's default for that role (the family doctor for "my doctor")
#   family_label -> the user's word for a family member ("Amma" -> mother)
#   usual        -> the user's usual business ("the usual pharmacy")
#   ambiguous    -> several people fit and nothing separates them: ask the user
ResolutionReason = Literal["clue", "primary", "family_label", "usual", "ambiguous"]

# What Pehchaan is expected to do with the sentence:
#   correct -> the names are in the KB: fix any mis-hearing to the canonical spelling
#   keep    -> leave the text alone and link nothing (unknown names, or no names at all)
#   resolve -> near-identical candidates exist, but context picks the right one
#   clarify -> the system cannot safely decide, so it should ASK the user
# (For the "reference" category, resolve = work out who "my doctor" / "Amma" means.)
Behaviour = Literal["correct", "keep", "resolve", "clarify"]


class EntitySpan(BaseModel):
    """One name mentioned in the sentence."""

    model_config = {"extra": "forbid"}

    surface: str = Field(min_length=1)  # the exact text as it appears in the sentence
    entity_id: str | None  # the correct KB id, or None if it must NOT be linked to the KB
    type: Literal["person", "place", "business"]


class ReferenceSpan(BaseModel):
    """A personal reference in the sentence ("my doctor", "Amma", "the usual pharmacy").

    Unlike an EntitySpan, the words are not a name: we must work out WHO is meant
    from the user's personal context (roles, defaults, family labels, usual places).
    """

    model_config = {"extra": "forbid"}

    surface: str = Field(min_length=1)  # exact phrase in the sentence, e.g. "my doctor"
    resolved_entity_id: str | None  # who it means, or None when we must ask
    resolution_reason: ResolutionReason

    @model_validator(mode="after")
    def ambiguous_means_unresolved(self):
        # "ambiguous" and "no answer" must go together: either we know who, or we ask.
        if (self.resolution_reason == "ambiguous") != (self.resolved_entity_id is None):
            raise ValueError(f"{self.surface!r}: use reason 'ambiguous' exactly when resolved_entity_id is null")
        return self


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
    # Personal references ("my doctor", "Amma"). Only used by the "reference" category.
    references: list[ReferenceSpan] = []
    expected_behaviour: Behaviour
    # Other behaviours that also count as correct. Example: for "Remind me to call Rohan"
    # (Rohan is not a contact, Rohit is), keeping "Rohan" is expected, but asking
    # "did you mean Rohit?" is also fine. Silently resolving to Rohit is NOT.
    also_acceptable: list[Behaviour] = []
    # The KB ids to ask about when clarifying (required for clarify; allowed when
    # clarify is one of the acceptable behaviours).
    candidate_ids: list[str] = []
    expected_action: ExpectedAction

    @model_validator(mode="after")
    def check_internal_consistency(self):
        # Every entity surface must literally appear in the text. Later modules
        # score span detection on exact text, so a mismatch would corrupt the scores.
        for span in [*self.entities, *self.references]:
            if span.surface not in self.text:
                raise ValueError(f"{self.id}: surface {span.surface!r} not found in text")

        # Outgoing commands have no caller. Only incoming calls can come from a contact.
        if self.direction == "outgoing" and self.caller_contact_id is not None:
            raise ValueError(f"{self.id}: outgoing sentence cannot have a caller_contact_id")

        # Candidates are only meaningful when the answer is "ask the user".
        if self.expected_behaviour == "clarify" and not self.candidate_ids:
            raise ValueError(f"{self.id}: clarify needs at least one candidate id")
        clarify_ok = self.expected_behaviour == "clarify" or "clarify" in self.also_acceptable
        if self.candidate_ids and not clarify_ok:
            raise ValueError(f"{self.id}: candidate_ids are only allowed when clarify is acceptable")
        if self.expected_behaviour in self.also_acceptable:
            raise ValueError(f"{self.id}: also_acceptable must not repeat expected_behaviour")

        # When we must ask first, the action cannot already have a target.
        if self.expected_behaviour == "clarify" and self.expected_action.target_entity_id is not None:
            raise ValueError(f"{self.id}: a clarify sentence cannot have an action target yet")
        return self


class RealSpeechClip(BaseModel):
    """One clip of REAL human speech (AI4Bharat Svarah sample), listed in data/realspeech/manifest.json.

    These are not our sentences: they are real Indian-accented speakers saying everyday English.
    They mostly contain none of our KB names, so the expected behaviour is "keep". They test the
    key safety question: does Pehchaan make a real transcript WORSE (over-correction)?
    """

    model_config = {"extra": "forbid"}

    id: str = Field(pattern=r"^r\d{3}$")  # "r001"
    split: Literal["dev", "test"]
    category: Literal["real_speech"] = "real_speech"
    text: str = Field(min_length=1)  # the dataset's human reference transcript
    speaker_id: str = Field(min_length=1)
    audio_path: str  # relative to the project root, forward slashes
    duration_seconds: float = Field(gt=0)
    expected_behaviour: Behaviour = "keep"
    source: str  # e.g. "ai4bharat/Svarah"
    source_id: str  # the row / file id in the source dataset, for attribution and traceability
