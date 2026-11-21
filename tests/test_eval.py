"""
tests/test_eval.py — tests for the evaluation framework and baseline (c) (Module 5).

WHAT: Hand-made examples for every important scoring rule: raw counts, an invalid id counted as a
      wrong target, clarify vs resolve scoring, over-correction detection, the decision schema,
      the time normaliser, the cache rule, baseline (c) with a FAKE OpenAI client, and the
      held-out rule in evaluate.py.
WHY:  If the scoring is wrong, every reported number is wrong. These tests are free and offline.

Run with:  pytest -v
"""

import json
import subprocess
import sys
from types import SimpleNamespace

import pytest

from app.baselines import llm_resolver
from app.eval import metrics
from app.eval.decision import ActionDecision, Decision, EntityDecision
from app.eval.runs import todo_clips
from app.eval.timeparse import normalise_time
from app.kb.loader import load_kb
from app.testset.validate import load_testset

KB_ID = {e.name: e.id for e in load_kb()}
SENT = {s.id: s for s in load_testset()}


def by_text(fragment: str):
    return next(s for s in SENT.values() if fragment in s.text)


def decision(behaviour="correct", target=None, place=None, time=None, entities=(), candidates=(),
             text="", used_llm=True):
    """Helper: build a Decision with sensible defaults."""
    return Decision(
        clip_id="s999", system_name="test", heard_transcript=text, output_transcript=text,
        behaviour=behaviour, clarify_candidates=list(candidates),
        entities=[EntityDecision(heard_text=h, resolved_entity_id=i, confidence=0.9, reason="test")
                  for h, i in entities],
        action=ActionDecision(type="remind" if target else "none", target_entity_id=target,
                              place_entity_id=place, time=time),
        used_llm=used_llm, latency_ms=100, cost_usd=0.001,
    )


# --- Count / raw counts ---

def test_count_shows_raw_counts():
    c = metrics.Count()
    for hit in (True, True, False):
        c.add(hit)
    assert str(c) == "2/3 = 67%"
    assert str(metrics.Count()) == "0/0 = n/a"


# --- Decision schema ---

def test_decision_rejects_bad_time_format():
    with pytest.raises(ValueError):
        ActionDecision(type="remind", time="7pm")


def test_invalid_id_does_not_crash_and_counts_as_wrong_target():
    gt = by_text("Call Dr. Venkataramana and ask")
    d = decision(target="person_999")  # this id does not exist
    assert d.invalid_ids() == ["person_999"]
    assert metrics.wrong_target(gt, d) is True


# --- Clarify vs resolve scoring ---

def test_acting_when_should_ask_is_missed_clarification_and_wrong_target():
    gt = by_text("Call Harshit at 5.")  # expected: clarify between Harshit and Harshil
    guessed = decision("resolve", target=KB_ID["Harshit Sharma"])
    m = metrics.decision_metrics([(gt, guessed)])
    assert str(m["missed_clarification_rate"]) == "1/1 = 100%"
    assert str(m["wrong_target_rate"]) == "1/1 = 100%"


def test_rightly_asking_scores_well_and_takes_no_action():
    gt = by_text("Call Harshit at 5.")
    asked = decision("clarify", target=KB_ID["Harshit Sharma"],  # target filled in, but clarify acts on nobody
                     candidates=[KB_ID["Harshit Sharma"], KB_ID["Harshil Patel"]])
    assert metrics.effective_target(asked) is None
    m = metrics.decision_metrics([(gt, asked)])
    assert str(m["missed_clarification_rate"]) == "0/1 = 0%"
    assert str(m["wrong_target_rate"]) == "0/1 = 0%"
    assert str(m["clarify_candidates_ok"]) == "1/1 = 100%"


def test_asking_when_answer_is_clear_is_an_unnecessary_question():
    gt = by_text("Call Dr. Venkataramana and ask")
    m = metrics.decision_metrics([(gt, decision("clarify", candidates=[KB_ID["Dr. Venkataramana"]]))])
    assert str(m["unnecessary_question_rate"]) == "1/1 = 100%"
    assert str(m["behaviour_accuracy"]) == "0/1 = 0%"


def test_exact_action_needs_target_and_place():
    gt = by_text("Book a table for four at Kakatiya Kitchen")  # place: Madhapur
    right = decision(target=KB_ID["Kakatiya Kitchen"], place=KB_ID["Madhapur"])
    no_place = decision(target=KB_ID["Kakatiya Kitchen"])
    assert metrics.action_exact(gt, right) is True
    assert metrics.action_exact(gt, no_place) is False


def test_reference_resolution_clue_beats_default():
    gt = by_text("my tooth is paining")
    dentist = decision("resolve", target=KB_ID["Dr. Subramanian"],
                       entities=[("my doctor", KB_ID["Dr. Subramanian"])])
    default = decision("resolve", target=KB_ID["Dr. Venkataramana"],
                       entities=[("my doctor", KB_ID["Dr. Venkataramana"])])
    assert metrics.reference_ok(gt, dentist) is True
    assert metrics.reference_ok(gt, default) is False
    assert metrics.wrong_target(gt, default) is True


# --- Over-correction ---

def test_over_correction_detected_in_transcript_and_in_links():
    gt = by_text("The cook at the polling booth")  # control: nothing should be linked
    assert metrics.over_corrected(gt, "The cook at Kukatpally said lunch is ready.") is True
    assert metrics.over_corrected(gt, gt.text) is False
    linked = decision("correct", entities=[("cook", KB_ID["Kukatpally"])], text=gt.text)
    assert metrics.over_corrected(gt, gt.text, linked) is True


def test_over_correction_only_counts_keep_categories():
    assert metrics.over_corrected(by_text("Call Dr. Venkataramana and ask"), "anything") is None


def test_transcript_metrics_entity_accuracy_and_wer():
    gt = by_text("Call Dr. Venkataramana and ask")
    m = metrics.transcript_metrics([(gt, "Call doctor Venkat Ramana and ask if he is free this evening.", None)])
    assert str(m["entity_accuracy"]) == "0/1 = 0%"  # "doctor" == "Dr." but "Venkat Ramana" is wrong
    assert m["wer"].hits > 0 and m["wer"].total == 11  # 11 reference words


# --- Time normaliser ---

@pytest.mark.parametrize("text, expected", [
    ("tomorrow at 10 AM", "10:00"), ("8 PM tonight", "20:00"), ("kal shaam saat baje", "19:00"),
    ("six thirty tomorrow morning", "06:30"), ("at 5", None), ("the 10th", None), ("next week", None),
])
def test_normalise_time(text, expected):
    assert normalise_time(text) == expected


# --- Cache + baseline (c) with a fake client ---

def test_cache_skips_clips_with_saved_decisions():
    clips = [{"id": "s001"}, {"id": "s002"}]
    assert todo_clips(clips, {"clips": {"s001": {}}}) == [{"id": "s002"}]


def test_llm_resolver_with_fake_client():
    answer = {"output_transcript": "Call Dr. Raju.", "behaviour": "correct",
              "entities": [{"heard_text": "Dr. Raju", "resolved_entity_id": KB_ID["Dr. Raju"],
                            "confidence": 1.4, "reason": "exact"}],  # 1.4 must be clamped to 1.0
              "clarify_candidates": [],
              "action": {"type": "remind", "target_entity_id": KB_ID["Dr. Raju"], "place_entity_id": None,
                         "time": "7pm", "raw_time_text": "at 7pm"}}  # bad time format must be dropped
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        usage = SimpleNamespace(prompt_tokens=1000, completion_tokens=100,
                                prompt_tokens_details=SimpleNamespace(cached_tokens=0))
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(answer)))],
                               usage=usage)

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    d = llm_resolver.resolve("s999", "Call doctor Raju.", client=client)
    assert d.system_name == "llm_baseline" and d.used_llm
    assert d.entities[0].confidence == 1.0 and d.action.time is None
    assert d.cost_usd == pytest.approx(1000 * 0.15e-6 + 100 * 0.6e-6)
    sent = calls[0]
    assert sent["response_format"]["json_schema"]["strict"] is True
    assert "Dr. Raju" in sent["messages"][0]["content"]  # the full personal context is in the prompt
    assert "Outgoing" in sent["messages"][1]["content"]


def test_schema_restricts_ids_to_kb():
    enum = llm_resolver.output_schema()["$defs"]["EntityId"]["enum"]
    assert set(enum) == set(KB_ID.values())


# --- Held-out rule ---

def test_evaluate_refuses_test_split_without_final():
    result = subprocess.run([sys.executable, "scripts/evaluate.py", "--split", "test"],
                            capture_output=True, text=True)
    assert result.returncode == 1
    assert "held out" in result.stdout


# --- The shared --audio option of the runner scripts (Module 9, Step 0) -----------------------------
# Bug it guards against: "run_baseline.py --audio clean --audio phone" used to run phone ONLY,
# because argparse kept just the last value.
import argparse  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402

from app.eval.runs import add_audio_argument, chosen_audios  # noqa: E402


def _audios(argv, default=("clean", "phone")):
    parser = argparse.ArgumentParser()
    add_audio_argument(parser, default=default)
    return chosen_audios(parser.parse_args(argv))


def test_audio_option_accepts_several_values_in_both_forms():
    assert _audios(["--audio", "clean", "phone", "real"]) == ["clean", "phone", "real"]
    assert _audios(["--audio", "clean", "--audio", "phone"]) == ["clean", "phone"]  # the old bug
    assert _audios(["--audio", "real", "clean", "real"]) == ["clean", "real"]  # fixed order, no duplicates
    assert _audios(["--audio", "all"]) == ["clean", "phone", "real"]
    assert _audios([]) == ["clean", "phone"]  # the default is used, not extended


def test_every_runner_uses_the_shared_audio_option_and_guards_the_test_split():
    for script in ("run_baseline.py", "run_llm_baseline.py", "run_pehchaan.py"):
        # --help costs nothing (no API calls): it proves the option parses as "one or more".
        out = subprocess.run([sys.executable, f"scripts/{script}", "--help"], capture_output=True, text=True)
        assert out.returncode == 0 and "--audio" in out.stdout and "[--audio" in out.stdout, script
        assert "AUDIO [AUDIO ...]" in out.stdout.replace("{clean,phone,real,all}", "AUDIO"), script
        # Without --final, the held-out split is refused BEFORE anything is loaded or spent.
        stop = subprocess.run([sys.executable, f"scripts/{script}", "--split", "test", "--audio", "clean", "phone"],
                              capture_output=True, text=True)
        assert stop.returncode == 1 and "[STOP]" in stop.stdout, script
