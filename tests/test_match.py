"""
tests/test_match.py — tests for candidate spans and phonetic matching (Modules 6+7).

WHAT: Phonetic keys on real mishearings ("Aunt Johnny" ~ "Anjani", "a bit" ~ "Abids",
      "the roomer life" ~ "Thirumalai"), transliteration of Indian scripts, the common-word protection
      ("lucky", "the cook", "said"), personal-reference detection ("my doctor" -> 3 doctors, "Amma"),
      non-max suppression, and speed (< 50 ms per sentence). No LLM, no network.
WHY:  These are the behaviours Module 8 relies on; if one breaks, the decisions break.

Run with:  pytest -v
"""

import time

import pytest

from app.kb.loader import get_by_role, load_kb
from app.match.candidates import find_candidates
from app.match.phonetic import indian_phonetic_key, metaphone_keys, phonetic_similarity
from app.match.translit import transliterate

KB_ID = {e.name: e.id for e in load_kb()}


def top_ids(span):
    return [c.entity_id for c in span.candidates]


# --- Phonetic keys ---

@pytest.mark.parametrize("heard, name", [
    ("Aunt Johnny", "Anjani"), ("a bit", "Abids"), ("the roomer life", "Thirumalai"),
    ("cook at Polly", "Kukatpally"), ("Chicana", "Chikkanna"), ("sweetie", "Swati"),
])
def test_mishearings_sound_alike(heard, name):
    assert phonetic_similarity(heard, name) >= 0.65


def test_unrelated_words_sound_less_alike():
    assert phonetic_similarity("lucky", "Thirumalai") < 0.5
    assert phonetic_similarity("cook at Polly", "Kukatpally") > phonetic_similarity("cook", "Kukatpally")


@pytest.mark.parametrize("a, b", [("Thakkar", "Takar"), ("Swathi", "Svati"), ("Keerthi", "Kirti"),
                                  ("Madhapur", "Madapur"), ("Zehra", "Jehra"), ("Sharma", "Sarma")])
def test_indian_sound_rules(a, b):
    assert indian_phonetic_key(a) == indian_phonetic_key(b)


def test_metaphone_makes_cook_at_polly_identical_to_kukatpally():
    assert set(metaphone_keys("cook at polly")) & set(metaphone_keys("Kukatpally"))


def test_transliterates_devanagari_and_telugu():
    assert transliterate("कल तक") == "kal tak"
    assert transliterate("కుకట్పల్లి") == "kukatpalli"


# --- Common-word protection ---

@pytest.mark.parametrize("text", [
    "The cook at the polling booth said lunch is ready.",
    "We are lucky the rain stopped before the match.",
    "Remind me to buy roses for the anniversary on Saturday.",
])
def test_control_sentences_have_no_confident_candidates(text):
    assert all(s.candidates[0].score < 0.8 for s in find_candidates(text))


def test_said_is_not_sid_and_kal_tak_is_not_cuttack():
    for text, wrong in [("He said it was fine.", "Siddharth Deshpande"), ("स्टेशनरी कल तक रेडी हो जाएगी", "Cuttack")]:
        assert all(not (c.entity_id == KB_ID[wrong] and c.score >= 0.8) for s in find_candidates(text) for c in s.candidates)


# --- Personal references ---

def test_my_doctor_lists_all_three_doctors_and_marks_default():
    spans = [s for s in find_candidates("Call my doctor, my tooth is paining.") if s.kind == "reference"]
    assert len(spans) == 1 and spans[0].heard_text == "my doctor"
    assert set(top_ids(spans[0])) == {e.id for e in get_by_role("doctor")}
    assert any("DEFAULT for doctor" in r for c in spans[0].candidates for r in c.reasons)


def test_family_label_amma_and_telugu_nanna():
    amma = [s for s in find_candidates("Remind me to call Amma at 7.") if s.kind == "reference"]
    assert top_ids(amma[0]) == [KB_ID["Sarojini Rao"]]
    nanna = [s for s in find_candidates("నాన్న కి కాల్ చేయి") if s.kind == "reference"]
    assert top_ids(nanna[0]) == [KB_ID["Ramachandra Rao"]]


def test_ramulu_anna_is_a_name_not_the_users_brother():
    spans = find_candidates("Sir, Ramulu Anna here, tomatoes are fresh.")
    assert not any(s.kind == "reference" for s in spans)
    assert any(top_ids(s)[0] == KB_ID["Ramulu Anna"] for s in spans)


def test_usual_pharmacy_and_the_electrician():
    spans = find_candidates("Order Amma's tablets from the usual pharmacy.")
    refs = {s.heard_text: top_ids(s) for s in spans if s.kind == "reference"}
    assert refs["the usual pharmacy"] == [KB_ID["Sri Venkateswara Pharmacy"]]
    assert refs["Amma's"] == [KB_ID["Sarojini Rao"]]
    elec = [s for s in find_candidates("Call the electrician, the fan is not working.") if s.kind == "reference"]
    assert len(top_ids(elec[0])) == 2


# --- Non-max suppression + output shape ---

def test_spans_never_overlap_and_have_at_most_three_candidates():
    spans = find_candidates("Book a table for four at Cockatiel Kitchen in Maghapur for 8 p.m. tonight.")
    for a in spans:
        assert len(a.candidates) <= 3
        assert a.margin >= 0
        for b in spans:
            assert a is b or a.end <= b.start or b.end <= a.start
    names = {top_ids(s)[0] for s in spans if s.kind == "name"}
    assert KB_ID["Kakatiya Kitchen"] in names and KB_ID["Madhapur"] in names


def test_heard_text_points_back_into_the_transcript():
    text = "Call Chicana here about the plants."
    for s in find_candidates(text):
        assert text[s.start:s.end] == s.heard_text


# --- Speed ---

def test_well_under_50ms_per_sentence():
    sentences = ["Call Aunt Johnny and ask if Matt's tuition is on this evening.",
                 "The roomer Life Selvan will pay the rent late this month. Remind me on the 10th.",
                 "Book a table for four at Cockatiel Kitchen in Maghapur for 8 p.m. tonight."] * 5
    find_candidates("warm up")  # first call builds the index
    start = time.perf_counter()
    for s in sentences:
        find_candidates(s)
    mean_ms = (time.perf_counter() - start) * 1000 / len(sentences)
    assert mean_ms < 50
