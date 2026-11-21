"""
tests/test_testset.py — automated checks for the test set (Module 3).

WHAT: Confirms sentences.json loads, passes every KB cross-check, has the planned size and
      split, covers the key scenarios (Raju Hotel, unknown-caller Raju, Harshit/Harshil),
      and that the validator really rejects broken entries.
WHY:  The test set is our answer key. A silent mistake here would make every reported metric wrong.

Run with:  pytest -v
"""

import pytest

from app.kb.loader import _normalise, all_surface_forms, load_kb
from app.testset.models import RealSpeechClip, Sentence
from app.testset.validate import (
    TestsetValidationError,
    load_realspeech,
    load_testset,
    validate_realspeech,
    validate_testset,
)

KB_ID = {e.name: e.id for e in load_kb()}


def by_text(fragment: str) -> Sentence:
    """Helper: the one sentence whose text contains this fragment."""
    matches = [s for s in load_testset() if fragment in s.text]
    assert len(matches) == 1, f"expected one sentence containing {fragment!r}"
    return matches[0]


def test_testset_loads_and_validates():
    sentences = load_testset()
    validate_testset(sentences)  # raises if any rule is broken


def test_every_entity_id_exists_in_kb():
    known = set(KB_ID.values())
    for s in load_testset():
        for span in s.entities:
            assert span.entity_id is None or span.entity_id in known, s.id


def test_size_and_split():
    sentences = load_testset()
    assert 160 <= len(sentences) <= 170
    dev = [s for s in sentences if s.split == "dev"]
    assert 60 <= len(dev) <= 70  # roughly a third held for tuning; the rest held out


def test_every_category_in_both_splits():
    sentences = load_testset()
    for split in ("dev", "test"):
        cats = {s.category for s in sentences if s.split == split}
        assert cats == {"in_kb", "out_of_kb", "control", "ambiguous", "context_mismatch", "reference",
                        "unfamiliar_near_match", "stale_default"}


def test_category_sizes():
    sentences = load_testset()
    count = lambda c: sum(s.category == c for s in sentences)  # noqa: E731
    assert 75 <= count("in_kb") <= 85
    assert 10 <= count("out_of_kb") <= 15
    assert 10 <= count("control") <= 15
    assert 12 <= count("ambiguous") <= 16
    assert 8 <= count("context_mismatch") <= 12
    assert 19 <= count("reference") <= 25
    assert 5 <= count("unfamiliar_near_match") <= 8
    assert 5 <= count("stale_default") <= 8


def test_out_of_kb_names_are_really_unknown():
    forms = all_surface_forms()
    for s in load_testset():
        if s.category == "out_of_kb":
            for span in s.entities:
                assert _normalise(span.surface) not in forms, f"{s.id}: {span.surface}"


def test_raju_hotel_asks_about_dr_raju():
    s = by_text("Raju Hotel")
    assert s.expected_behaviour == "clarify"
    assert s.candidate_ids == [KB_ID["Dr. Raju"]]


def test_unknown_caller_raju_is_not_linked():
    s = by_text("Raju from the bank")
    assert s.direction == "incoming" and s.caller_contact_id is None
    assert s.expected_behaviour == "keep"
    assert all(span.entity_id is None for span in s.entities)


def test_harshil_resolves_by_context_and_harshit_alone_clarifies():
    resolved = by_text("Ask Harshil to send the invoice")
    assert resolved.expected_behaviour == "resolve"
    assert resolved.entities[0].entity_id == KB_ID["Harshil Patel"]

    unclear = by_text("Call Harshit at 5.")
    assert unclear.expected_behaviour == "clarify"
    assert set(unclear.candidate_ids) == {KB_ID["Harshit Sharma"], KB_ID["Harshil Patel"]}


def test_has_code_mixed_lines():
    # Hinglish / Tenglish markers must appear in a few lines.
    texts = [s.text.lower() for s in load_testset()]
    assert sum(any(w in t for w in (" ko ", " hai", " ga ", "cheyyi", " lo ")) for t in texts) >= 5


# --- The validators must reject broken data ---

def base(**overrides) -> dict:
    """A valid minimal sentence; tests override one field to break it."""
    row = {
        "id": "s999", "split": "dev", "text": "Call Dr. Raju at 5.", "category": "in_kb",
        "direction": "outgoing", "caller_contact_id": None,
        "entities": [{"surface": "Dr. Raju", "entity_id": KB_ID["Dr. Raju"], "type": "person"}],
        "expected_behaviour": "correct", "candidate_ids": [],
        "expected_action": {"type": "call", "target_entity_id": KB_ID["Dr. Raju"], "time": "5"},
    }
    row.update(overrides)
    return row


def test_model_rejects_surface_not_in_text():
    with pytest.raises(ValueError, match="not found in text"):
        Sentence.model_validate(base(text="Call the doctor at 5."))


def test_model_rejects_clarify_without_candidates():
    with pytest.raises(ValueError, match="clarify needs"):
        Sentence.model_validate(base(expected_behaviour="clarify"))


def test_validator_rejects_unknown_kb_id():
    bad = Sentence.model_validate(
        base(entities=[{"surface": "Dr. Raju", "entity_id": "person_999", "type": "person"}])
    )
    with pytest.raises(TestsetValidationError, match="not in the KB"):
        validate_testset([bad])


def test_in_kb_surfaces_are_canonical_names():
    names = {e.id: e.name for e in load_kb()}
    for s in load_testset():
        if s.category == "in_kb":
            for span in s.entities:
                assert span.surface == names[span.entity_id], s.id


def test_callers_are_kb_persons_and_null_for_outgoing():
    persons = {e.id for e in load_kb() if e.type == "person"}
    for s in load_testset():
        if s.direction == "outgoing":
            assert s.caller_contact_id is None, s.id
        else:
            assert s.caller_contact_id is None or s.caller_contact_id in persons, s.id


def test_validator_rejects_alias_as_in_kb_surface():
    bad = Sentence.model_validate(base(
        text="Call Raju at 5.",
        entities=[{"surface": "Raju", "entity_id": KB_ID["Dr. Raju"], "type": "person"}],
    ))
    with pytest.raises(TestsetValidationError, match="not the canonical name"):
        validate_testset([bad])


def test_validator_rejects_out_of_kb_name_that_is_in_kb():
    bad = Sentence.model_validate(base(
        category="out_of_kb", expected_behaviour="keep", text="Call Kukatpally.",
        entities=[{"surface": "Kukatpally", "entity_id": None, "type": "place"}],
        expected_action={"type": "none"},
    ))
    with pytest.raises(TestsetValidationError, match="IS in the KB"):
        validate_testset([bad])


# --- Vision upgrade: the "reference" category ("my doctor", "Amma", "the usual pharmacy") ---

def ref_of(fragment: str):
    """Helper: the sentence and its first reference."""
    s = by_text(fragment)
    return s, s.references[0]


def test_reference_clue_tooth_means_dentist():
    s, r = ref_of("my tooth is paining")
    assert s.expected_behaviour == "resolve"
    assert (r.resolved_entity_id, r.resolution_reason) == (KB_ID["Dr. Subramanian"], "clue")


def test_reference_plain_my_doctor_means_default_doctor():
    s, r = ref_of("Call my doctor.")
    assert (r.resolved_entity_id, r.resolution_reason) == (KB_ID["Dr. Venkataramana"], "primary")


def test_reference_family_label_and_usual_business():
    s = by_text("the usual pharmacy")
    resolved = {r.surface: (r.resolved_entity_id, r.resolution_reason) for r in s.references}
    assert resolved["Amma"] == (KB_ID["Sarojini Rao"], "family_label")
    assert resolved["the usual pharmacy"] == (KB_ID["Sri Venkateswara Pharmacy"], "usual")


def test_reference_combined_with_misheard_name():
    s, r = ref_of("eye checkup")
    assert r.resolved_entity_id == KB_ID["Dr. Raju"]
    assert [span.entity_id for span in s.entities] == [KB_ID["Kukatpally"]]


def test_reference_ambiguous_colleague_asks_with_all_colleagues():
    s, r = ref_of("join the call")
    assert s.expected_behaviour == "clarify" and r.resolution_reason == "ambiguous"
    assert set(s.candidate_ids) == {e.id for e in load_kb() if "colleague" in e.context.get("roles", [])}


def test_references_only_in_reference_style_categories():
    for s in load_testset():
        assert (s.category in ("reference", "stale_default")) == bool(s.references), s.id


def test_validator_rejects_wrong_reason():
    # Claiming "primary" for someone who is not a default for any role must fail.
    bad = Sentence.model_validate(base(
        category="reference", expected_behaviour="resolve", text="Call my dentist.", entities=[],
        references=[{"surface": "my dentist", "resolved_entity_id": KB_ID["Dr. Subramanian"],
                     "resolution_reason": "primary"}],
        expected_action={"type": "call", "target_entity_id": KB_ID["Dr. Subramanian"]},
    ))
    with pytest.raises(TestsetValidationError, match="not a default"):
        validate_testset([bad])


def test_model_rejects_ambiguous_reference_with_an_answer():
    with pytest.raises(ValueError, match="ambiguous"):
        Sentence.model_validate(base(
            category="reference", text="Call my doctor.", entities=[],
            references=[{"surface": "my doctor", "resolved_entity_id": KB_ID["Dr. Raju"],
                         "resolution_reason": "ambiguous"}],
        ))


# --- Judge review: unfamiliar near-matches, stale defaults, real speech ---

def test_unfamiliar_near_match_is_never_resolved():
    # "Rohan" is one sound away from contact Rohit, but is NOT a contact:
    # keep it (or clarify), never link it, never give the action a KB target.
    forms = all_surface_forms()
    near = [s for s in load_testset() if s.category == "unfamiliar_near_match"]
    assert near
    for s in near:
        assert s.expected_behaviour == "keep" and "clarify" in s.also_acceptable
        assert all(span.entity_id is None for span in s.entities)
        assert all(_normalise(span.surface) not in forms for span in s.entities)
        assert s.expected_action.target_entity_id is None


def test_harshil_mehta_is_not_harshil_patel():
    s = by_text("Harshil Mehta")
    assert s.entities[0].entity_id is None
    assert s.candidate_ids == [KB_ID["Harshil Patel"]]


def test_stale_default_clue_beats_default_doctor():
    s, r = ref_of("eye drops")
    assert s.category == "stale_default"
    assert (r.resolved_entity_id, r.resolution_reason) == (KB_ID["Dr. Raju"], "clue")
    assert r.resolved_entity_id != KB_ID["Dr. Venkataramana"]  # the (stale) default


def test_model_rejects_candidates_when_clarify_not_acceptable():
    with pytest.raises(ValueError, match="only allowed when clarify"):
        Sentence.model_validate(base(candidate_ids=[KB_ID["Dr. Raju"]]))


def test_realspeech_manifest_is_valid_if_present():
    # The sample needs a gated download (HF token), so it may not exist yet.
    validate_realspeech(load_realspeech())


def test_realspeech_validator_needs_audio_and_several_speakers(tmp_path):
    (tmp_path / "a.wav").write_bytes(b"")
    clips = [RealSpeechClip(id=f"r00{i}", split="test", text="hello", speaker_id="same", audio_path="a.wav",
                            duration_seconds=2.0, source="ai4bharat/Svarah", source_id=str(i)) for i in range(1, 7)]
    with pytest.raises(TestsetValidationError, match="different speakers"):
        validate_realspeech(clips, root=tmp_path)
    # Partly downloaded (one file there, one missing) is an error...
    partial = [clips[0], clips[1].model_copy(update={"audio_path": "nope.wav", "speaker_id": "other"})]
    with pytest.raises(TestsetValidationError, match="audio file missing"):
        validate_realspeech(partial, root=tmp_path)


def test_realspeech_without_any_audio_is_valid(tmp_path):
    # ...but NO audio at all is fine: the audio isn't in git and is fetched separately (fetch_real_speech.py).
    clips = [RealSpeechClip(id=f"r00{i}", split="test", text="hello", speaker_id=f"s{i}", audio_path=f"x{i}.wav",
                            duration_seconds=2.0, source="ai4bharat/Svarah", source_id=str(i)) for i in range(1, 7)]
    validate_realspeech(clips, root=tmp_path)


def test_test2_is_sealed_and_complete():
    # test-2 (s164-s208) is the second held-out set, frozen at tag test2-frozen BEFORE Pehchaan v2 ran on it.
    # Default loading never includes it, so no tuning/reporting code can see it by accident.
    assert all(s.split in ("dev", "test") for s in load_testset())
    t2 = load_testset(splits=("test2",))
    assert len(t2) == 45 and {s.id for s in t2} == {f"s{i}" for i in range(164, 209)}
    assert len({s.category for s in t2}) == 8  # every category is covered
    validate_testset(load_testset(splits=None))
