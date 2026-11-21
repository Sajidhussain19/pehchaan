"""
app/kb/models.py — Pydantic data models for the knowledge base.

WHAT: Defines what one knowledge-base entry (an `Entity`) looks like: its id, correct
      spelling, type, alternate spellings, language of origin, difficulty, and extra context.
      Also defines the shape of the context for each type (person / place / business), including
      the personal-reference fields (roles, default contacts, family labels, the usual shop),
      and `Preference`: a learned answer to "who did you mean?".
WHY:  The KB is hand-written JSON, and hand-written data has typos. Pydantic checks every
      entry when it is loaded. A missing field, a misspelled type ("persn") or a bad phone
      number fails loudly at load time, not in the middle of a demo.
"""

import re
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# `Literal` limits a field to a fixed set of values. Anything else is a validation error.
EntityType = Literal["person", "place", "business"]
Difficulty = Literal["easy", "medium", "hard"]

# All phone numbers are FAKE and follow one pattern: +91-90000-0XXXX.
# Checking the pattern makes sure no real-looking number slips into the data by accident.
FAKE_PHONE_PATTERN = re.compile(r"^\+91-90000-0\d{4}$")


# ---------------------------------------------------------------------------
# Context models: the extra info each type carries.
# extra="forbid" means an unknown key (e.g. a typo like "relaton") is an error.
# ---------------------------------------------------------------------------

class PersonContext(BaseModel):
    """Extra info about a contact. Later modules use it for actions like 'call'."""

    model_config = {"extra": "forbid"}

    relation: str  # how the user knows them, e.g. "family doctor", "cousin"
    phone: str  # fake number, used by the "call" action in Module 9
    notes: str = ""  # free text, can help the LLM check context in Module 8

    # --- Personal-reference fields (vision upgrade: "the personal ear") ---
    # Roles this person plays for the user, lower-case, e.g. ["doctor", "dentist"].
    # "Call my doctor" looks people up by role instead of by name.
    roles: list[str] = []
    # Roles for which this person is the user's DEFAULT, e.g. ["doctor"] for the family doctor.
    # When a role has several people and the sentence gives no clue, the default wins.
    is_primary_for: list[str] = []
    # What the user calls them at home, e.g. "Amma", "Nanna", "Akka". None for non-family.
    family_label: str | None = None
    # Fake date of the last call/message, a weak tie-breaker ("most recent interaction").
    last_interaction: date | None = None

    @field_validator("phone")
    @classmethod
    def phone_must_be_fake(cls, value: str) -> str:
        # Reject anything that is not in our fake-number format.
        if not FAKE_PHONE_PATTERN.match(value):
            raise ValueError(f"phone {value!r} must match the fake format +91-90000-0XXXX")
        return value

    @field_validator("roles", "is_primary_for")
    @classmethod
    def lower_case_roles(cls, value: list[str]) -> list[str]:
        # Store roles in lower case so "Doctor" and "doctor" are the same role.
        return [role.strip().lower() for role in value]

    @model_validator(mode="after")
    def primary_roles_are_roles(self):
        # You can only be the default doctor if you are a doctor.
        missing = set(self.is_primary_for) - set(self.roles)
        if missing:
            raise ValueError(f"is_primary_for {sorted(missing)} must also be listed in roles")
        return self


class PlaceContext(BaseModel):
    """Where a place is. 'kind' tells a whole city apart from a locality inside it."""

    model_config = {"extra": "forbid"}

    city: str
    state: str
    kind: Literal["locality", "city", "landmark"]


class BusinessContext(BaseModel):
    """What a business is and where. 'area' must be a place name from places.json."""

    model_config = {"extra": "forbid"}

    category: Literal["clinic", "hospital", "pharmacy", "restaurant", "salon", "school", "shop"]
    area: str
    city: str
    # "The usual pharmacy": is this the place the user normally goes to, and for what?
    is_usual: bool = False
    usual_for: str | None = None  # e.g. "pharmacy", "groceries", "salon"

    @model_validator(mode="after")
    def usual_fields_agree(self):
        # Both or neither: a usual place must say what it is usual for.
        if self.is_usual != (self.usual_for is not None):
            raise ValueError("is_usual and usual_for must be set together")
        return self


# Maps each entity type to the context model that validates it.
CONTEXT_MODELS: dict[str, type[BaseModel]] = {
    "person": PersonContext,
    "place": PlaceContext,
    "business": BusinessContext,
}


class Entity(BaseModel):
    """One thing Pehchaan can recognise: a person, a place or a business."""

    id: str = Field(pattern=r"^(person|place|business)_\d{3}$")  # e.g. "person_001"
    name: str = Field(min_length=1)  # the canonical (correct) spelling
    type: EntityType
    aliases: list[str] = []  # other common spellings, e.g. "Laxmi" for "Lakshmi"
    language_origin: str  # e.g. "Telugu", "Urdu"; useful for per-language results later
    difficulty: Difficulty  # how hard we expect speech-to-text to find it
    context: dict  # type-specific extra info, checked by the validator below

    @field_validator("name", "aliases")
    @classmethod
    def strip_and_reject_blank(cls, value):
        # Remove stray spaces at the ends and reject empty strings.
        # This runs on the name (a str) and on the aliases (a list of str).
        items = [value] if isinstance(value, str) else value
        cleaned = [item.strip() for item in items]
        if any(not item for item in cleaned):
            raise ValueError("names and aliases must not be empty")
        return cleaned[0] if isinstance(value, str) else cleaned

    @model_validator(mode="after")
    def check_context_and_id(self):
        # 1. The id prefix must match the type ("place_007" must have type "place").
        if not self.id.startswith(self.type + "_"):
            raise ValueError(f"id {self.id!r} does not match type {self.type!r}")
        # 2. Validate the context dict with the model for this type.
        #    We keep `context` as a plain dict (simple to read and to save as JSON),
        #    but we still check its shape strictly.
        CONTEXT_MODELS[self.type].model_validate(self.context)
        # 3. An alias that equals the name adds nothing, so treat it as a data mistake.
        if any(alias.lower() == self.name.lower() for alias in self.aliases):
            raise ValueError(f"{self.id}: an alias repeats the canonical name {self.name!r}")
        return self

    @property
    def surface_forms(self) -> list[str]:
        """Every way this entity may be written: the canonical name first, then the aliases."""
        return [self.name, *self.aliases]


class Preference(BaseModel):
    """A learned answer (level 4, "learning"). Saved after the user answers a clarify question.

    Example: the user said "call my colleague", we asked, they picked Harshil.
    We store {"phrase_pattern": "my colleague", "entity_id": "person_123", ...},
    so next time the same request resolves without asking. Written by Module 9.
    """

    model_config = {"extra": "forbid"}

    phrase_pattern: str = Field(min_length=1)  # the reference phrase, lower-case, e.g. "my colleague"
    entity_id: str  # what the user told us it means
    created_at: datetime  # when we learned it (ISO 8601 in the JSON file)

    @field_validator("phrase_pattern")
    @classmethod
    def normalise_phrase(cls, value: str) -> str:
        return " ".join(value.lower().split())
