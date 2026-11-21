"""
tests/test_decide.py — tests for Pehchaan's decision layer (Module 8).

WHAT: One small example per behaviour of the LangGraph pipeline:
      clue beats default, type mismatch, close tie -> ask, clue tie-break, unfamiliar-name guard,
      unknown caller, learned preference, time + place in the Remind action, the no-LLM path,
      and the LLM fallback with a FAKE client (no network, no cache file written).
WHY:  These are exactly the cases where the strong LLM baseline failed on dev. If one breaks,
      the headline results break.

Run with:  pytest -v
"""

import json
from datetime import datetime
from types import SimpleNamespace

from app.decide.graph import build_graph
from app.decide.pehchaan import resolve, trace
from app.kb.loader import get_by_role, load_kb
from app.kb.models import Preference

KB_ID = {e.name: e.id for e in load_kb()}


def test_clue_beats_default_tooth_means_dentist():
    d = resolve("Call my doctor, my tooth is paining.")
    assert d.behaviour == "resolve"
    assert d.action.target_entity_id == KB_ID["Dr. Subramanian"]  # not the default family doctor
    assert not d.used_llm and d.cost_usd == 0


def test_no_clue_uses_the_default():
    assert resolve("Call my doctor.").action.target_entity_id == KB_ID["Dr. Venkataramana"]


def test_type_mismatch_raju_hotel_asks_about_dr_raju():
    d = resolve("Book a table at Raju Hotel tomorrow at 9 AM.")
    assert d.behaviour == "clarify"
    assert d.clarify_candidates == [KB_ID["Dr. Raju"]]
    assert d.action.type == "none"  # never act before the user answers


def test_close_tie_without_clue_asks():
    d = resolve("Call Harshit at 5.")
    assert d.behaviour == "clarify"
    assert {KB_ID["Harshit Sharma"], KB_ID["Harshil Patel"]} <= set(d.clarify_candidates)


def test_clue_breaks_a_close_tie_after_mishearing():
    d = resolve("Ask Harshel to send the invoice by Friday.")
    assert d.behaviour == "resolve"
    assert d.action.target_entity_id == KB_ID["Harshil Patel"]  # 'invoice' -> accounts colleague
    assert "Harshil" in d.output_transcript  # what was heard is fixed in the text...
    assert d.entities[0].heard_text == "Harshel"  # ...but never hidden


def test_unfamiliar_name_guard_sravanthi_is_not_sravani():
    d = resolve("Remind me to call Sravanthi about the wedding card.")
    assert d.action.target_entity_id is None
    assert d.behaviour in ("clarify", "keep")
    assert "Sravani" not in d.output_transcript


def test_unknown_caller_with_a_contacts_name_is_kept():
    d = resolve("Hi, I'm Raju from the bank, calling about your credit card.", direction="incoming")
    assert d.behaviour == "keep" and d.action.target_entity_id is None


def test_learned_preference_is_used():
    colleagues = {e.id for e in get_by_role("colleague")}
    assert resolve("Ask my colleague to join the call.", preferences=[]).behaviour == "clarify"
    pref = Preference(phrase_pattern="my colleague", entity_id=KB_ID["Harshil Patel"], created_at=datetime(2026, 11, 21))
    d = resolve("Ask my colleague to join the call.", preferences=[pref])
    assert d.action.target_entity_id == KB_ID["Harshil Patel"] and KB_ID["Harshil Patel"] in colleagues


def test_remind_action_has_target_place_and_hhmm_time():
    d = resolve("Remind me to meet Gopikrishnan near Habsiguda at 7 PM.")
    assert d.action.type == "remind"
    assert d.action.target_entity_id == KB_ID["Gopikrishnan"]
    assert d.action.place_entity_id == KB_ID["Habsiguda"]
    assert d.action.time == "19:00"


def test_time_word_before_pm_wins_over_earlier_number_word():
    d = resolve("Tell Velu Anna to keep two cups of tea ready at four p.m.")
    assert d.action.time == "16:00"  # not 14:00 from "two cups"


def test_control_sentence_links_nothing_without_llm():
    d = resolve("The cook at the polling booth said lunch is ready.")
    assert d.behaviour == "keep" and not d.entities and not d.used_llm


def test_llm_fallback_with_fake_client():
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        answer = {"decisions": [{"phrase": 0, "choice": "keep", "reason": "a different person"}]}
        usage = SimpleNamespace(prompt_tokens=300, completion_tokens=40)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(answer)))],
                               usage=usage)

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    state = trace("Call Paige Sweeney and ask if she reached Nalgonda.", client=client)
    d = state["decision"]
    assert calls, "this unsure span should reach the LLM"
    assert d.used_llm and d.cost_usd > 0
    assert d.action.target_entity_id is None  # the LLM said keep
    sent = calls[0]
    assert sent["response_format"]["json_schema"]["strict"] is True
    assert "Nalgonda" in sent["messages"][1]["content"]  # only the sentence + candidates are sent
    assert "CONTACTS" not in sent["messages"][1]["content"]  # NOT the whole phone book


def test_graph_has_one_node_per_step():
    nodes = set(build_graph().get_graph().nodes)
    for step in ("preferences", "candidates", "references", "context_check", "route", "llm_fallback",
                 "action", "assemble"):
        assert step in nodes


def test_clue_beats_a_saved_preference():
    # Module 10 (approved change): the user said "always use the dentist for 'my doctor'", but "fever"
    # is a clue for the general physician, and a clue in the sentence wins (clue -> preference -> default -> ask).
    pref = Preference(phrase_pattern="my doctor", entity_id=KB_ID["Dr. Subramanian"], created_at=datetime(2026, 11, 21))
    d = resolve("Call my doctor about my fever and cough.", preferences=[pref], book="B")
    assert d.action.target_entity_id == KB_ID["Dr. Venkataramana"]
    assert "beats your saved choice" in d.entities[0].reason


def test_saved_preference_still_used_without_a_clue():
    pref = Preference(phrase_pattern="my doctor", entity_id=KB_ID["Dr. Subramanian"], created_at=datetime(2026, 11, 21))
    d = resolve("Remind me to call my doctor at 6 PM.", preferences=[pref], book="B")
    assert d.action.target_entity_id == KB_ID["Dr. Subramanian"] and "you told me" in d.entities[0].reason
    # The preference also beats the DEFAULT in the default book (family doctor is the default there).
    d = resolve("Remind me to call my doctor at 6 PM.", preferences=[pref])
    assert d.action.target_entity_id == KB_ID["Dr. Subramanian"]


# --- Pehchaan v2: over-correction fixes (fresh sentences, not from any test set) ------------------------

def test_v2_everyday_words_are_never_turned_into_names():
    # "ee roju" = "today" (Telugu); v1 turned "roju" into Dr. Raju. Same in Devanagari Hindi.
    for text in ("Ee roju chala busy ga unnanu, saayantram call chesta.", "आज बहुत गर्मी है, बाहर मत जाओ।"):
        d = resolve(text, preferences=[])
        assert d.behaviour == "keep" and not any(e.resolved_entity_id for e in d.entities), text


def test_v2_everyday_guard_keeps_real_names_and_exact_matches():
    assert resolve("Call Dr. Raju about my eye drops.", preferences=[]).action.target_entity_id == KB_ID["Dr. Raju"]


def test_v2_longest_match_prefers_the_business_over_a_first_name_inside_it():
    # v1 asked "which Lakshmi?" because the exact first name beat the slightly misheard business name.
    d = resolve("Order two plates of idli from Lakshmi Ganapati Tiffins.", preferences=[])
    assert d.behaviour != "clarify" and d.action.target_entity_id == KB_ID["Lakshmi Ganapathi Tiffins"]


def test_v2_longest_match_does_not_swallow_neighbouring_words():
    # Dev round 2: "Call Srinivasan Iyer" must not become one span (the correction would drop "Call").
    d = resolve("Call Srinivasan Iyer and wish him a happy birthday.", preferences=[])
    assert d.output_transcript.startswith("Call Srinivasan Iyer")


def test_v2_known_caller_introducing_themself_is_the_caller():
    d = resolve("Sir, Srinivas Gowd here, the car is washed and ready.", direction="incoming",
                caller_contact_id=KB_ID["Sreenivas Goud"], preferences=[])
    assert d.behaviour != "clarify" and d.entities[0].resolved_entity_id == KB_ID["Sreenivas Goud"]


def test_v2_unknown_caller_sharing_a_surname_is_not_linked():
    d = resolve("Hi, Ramesh Mehta from the bank, your loan papers are ready.", direction="incoming", preferences=[])
    assert not any(e.resolved_entity_id for e in d.entities) and d.action.target_entity_id is None


def test_v2_close_names_still_ask_and_llm_prompt_prefers_keep():
    from app.decide.llm_fallback import INSTRUCTIONS
    assert resolve("Call Harshit at 5.", preferences=[]).behaviour == "clarify"  # unchanged safety behaviour
    assert "A similar sound is" in INSTRUCTIONS and "keep" in INSTRUCTIONS
