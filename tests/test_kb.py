"""
tests/test_kb.py — automated checks for the knowledge base (Module 2).

WHAT: Confirms the KB loads, ids are unique, sizes are in the expected range, business areas
      exist, aliases never steal another entity's name, near-duplicates stay separate, and
      the validator really catches broken data.
WHY:  Every later module trusts the KB. If someone edits a JSON file and breaks a rule,
      these tests fail immediately and name the problem.

Run with:  pytest -v
"""

import pytest

from app.kb.loader import (
    KBValidationError,
    _normalise,
    all_surface_forms,
    get_by_id,
    get_by_type,
    load_kb,
    validate_entities,
)
from app.kb.models import Entity


def find(name: str) -> Entity:
    """Helper: return the entity with exactly this canonical name (fails the test if missing)."""
    matches = [e for e in load_kb() if e.name == name]
    assert len(matches) == 1, f"expected exactly one entity named {name!r}"
    return matches[0]


def test_kb_loads():
    kb = load_kb()
    assert len(kb) > 0
    assert all(isinstance(e, Entity) for e in kb)


def test_ids_are_unique():
    ids = [e.id for e in load_kb()]
    assert len(ids) == len(set(ids))


def test_counts_in_expected_range():
    # The brief asks for ~120 contacts, ~120 places, ~60 businesses.
    assert 100 <= len(get_by_type("person")) <= 150
    assert 100 <= len(get_by_type("place")) <= 160
    assert 50 <= len(get_by_type("business")) <= 80


def test_every_business_area_exists_in_places():
    place_names = {e.name for e in get_by_type("place")}
    for business in get_by_type("business"):
        assert business.context["area"] in place_names, business.id


def test_aliases_never_collide_with_another_entitys_name():
    canonical = {_normalise(e.name): e.id for e in load_kb()}
    for e in load_kb():
        for alias in e.aliases:
            owner = canonical.get(_normalise(alias))
            assert owner in (None, e.id), f"{alias!r} of {e.id} is the name of {owner}"


def test_near_duplicates_are_separate_entities():
    # These sound alike but are different people. They must never be merged.
    groups = [
        ["Srinivas Reddy", "Sreenivas Goud", "Srinivasan Iyer"],
        ["Ravi Teja", "Ravi Tej"],
        ["Lakshmi Prasanna", "Laxmi Devi"],
        ["Subrahmanyam Garu", "Dr. Subramanian"],
    ]
    for group in groups:
        ids = {find(name).id for name in group}
        assert len(ids) == len(group), f"near-duplicates merged: {group}"


NEAR_IDENTICAL_PAIRS = [
    ("Harshit Sharma", "Harshil Patel"),
    ("Rohit Chaturvedi", "Rohith Reddy"),
    ("Sai Kiran Rao", "Sai Kumar Yadav"),
    ("Anjali Verma", "Anjani Mishra"),
    ("Pranav Joshi", "Pranay Reddy"),
    ("Swathi Chowdary", "Swati Kulkarni"),
]


@pytest.mark.parametrize("name_a, name_b", NEAR_IDENTICAL_PAIRS)
def test_near_identical_pairs_are_separate_with_distinct_relations(name_a, name_b):
    # Module 3 mentor feedback: both halves of each pair exist as separate contacts,
    # and their relations differ, so context ("accounts", "gym") can tell them apart.
    a, b = find(name_a), find(name_b)
    assert a.id != b.id
    assert a.type == b.type == "person"
    assert a.context["relation"] != b.context["relation"]


def test_dr_raju_is_family_doctor_and_no_raju_hotel():
    # The context-mismatch test sentences rely on this: "Raju" in the KB is a doctor,
    # so "Raju Hotel" must NOT be linked to him without asking.
    assert find("Dr. Raju").context["relation"] == "family doctor"
    business_names = [e.name.lower() for e in get_by_type("business")]
    assert not any("raju hotel" in name for name in business_names)


def test_hard_cases_and_honorifics_are_present():
    # Long names, English-sounding places, and names with honorifics must all be in the KB.
    for name in ["Dr. Venkataramana", "Thiruvananthapuram", "Visakhapatnam", "Kukatpally",
                 "Ameerpet", "Begumpet", "Hitech City", "Smt. Padmavathi", "Sharma Ji", "Ramulu Anna"]:
        assert find(name).difficulty in ("medium", "hard")


def test_lookups_by_id_and_surface_form():
    assert get_by_id("person_001").name == "Dr. Venkataramana"
    assert get_by_id("does_not_exist") is None
    forms = all_surface_forms()
    # An alias leads back to its entity, and lookups ignore case.
    assert forms["laxmi prasanna"] == [find("Lakshmi Prasanna").id]
    assert forms["kukatpalli"] == [find("Kukatpally").id]


def test_kb_is_cached():
    # The cache returns new list objects built from the same Entity objects,
    # which proves the files were not read again.
    assert load_kb()[0] is load_kb()[0]


def test_phone_numbers_are_fake():
    for person in get_by_type("person"):
        assert person.context["phone"].startswith("+91-90000-0")


# --- The validator must catch broken data, not just pass good data ---

def make(id_, name, type_, aliases=(), context=None):
    """Helper: build a small valid Entity for the negative tests below."""
    default_context = {
        "person": {"relation": "friend", "phone": "+91-90000-09999"},
        "place": {"city": "Hyderabad", "state": "Telangana", "kind": "locality"},
        "business": {"category": "shop", "area": "Kukatpally", "city": "Hyderabad"},
    }[type_]
    return Entity(id=id_, name=name, type=type_, aliases=list(aliases), language_origin="Telugu",
                  difficulty="easy", context=context or default_context)


def test_validator_rejects_duplicate_ids():
    with pytest.raises(KBValidationError, match="duplicate id"):
        validate_entities([make("person_001", "A", "person"), make("person_001", "B", "person")])


def test_validator_rejects_alias_stealing_a_name():
    with pytest.raises(KBValidationError, match="canonical name"):
        validate_entities([make("person_001", "Srinivas", "person"),
                           make("person_002", "Sreenivas", "person", aliases=["Srinivas"])])


def test_validator_rejects_unknown_business_area():
    with pytest.raises(KBValidationError, match="unknown area"):
        validate_entities([make("business_001", "Some Shop", "business")])  # no places at all


def test_model_rejects_real_looking_phone():
    with pytest.raises(ValueError):
        make("person_001", "A", "person", context={"relation": "friend", "phone": "+91-98480-12345"})
