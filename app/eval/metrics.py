"""
app/eval/metrics.py — scores system outputs against the ground truth. Every metric is separate.

WHAT: Two families of metrics, each returned as raw counts ("7/12 = 58%"), never one blended score.

  Transcript-level (any system that outputs text: (a), (b), and the output_transcript of (c) / Pehchaan)
    - entity_accuracy: share of ground-truth KB names that appear correctly in the transcript
    - wer: word error rate of the whole sentence vs the reference (via jiwer)
    - over_correction_rate: on clips where nothing should be linked (control, out_of_kb, real_speech,
      unfamiliar_near_match), how often a KB entity APPEARED that wasn't in what was said
      (in the transcript, or, for decision systems, as a link)

  Decision-level (systems that output a Decision: (c) now, Pehchaan later)
    - behaviour_accuracy: correct / keep / resolve / clarify as expected (also_acceptable counts)
    - exact_action_target_accuracy: a Remind with the right target AND the right place
    - time_accuracy: the right "HH:MM" (only clips whose expected time is unambiguous)
    - wrong_target_rate: acted on the WRONG entity, or used an id that doesn't exist (worst error)
    - unnecessary_question_rate: asked when it should have just acted/kept
    - missed_clarification_rate: acted when it should have asked
    - clarify_candidates_ok: when it rightly asked, did it offer the right people?
    - reference_resolution_accuracy: "my doctor", "Amma", "the usual pharmacy" resolved correctly
    - no_llm_rate, latency (mean/median ms), mean cost per call

  Rule used everywhere: a "clarify" decision takes NO action yet (the reminder is only created after
  the user answers), even if the system also filled in a target.
WHY:  One blended number would hide the error that matters most (doing the wrong thing confidently).
      Raw counts show how much evidence sits behind each percentage.
"""

import re
import statistics
from dataclasses import dataclass

import jiwer

from app.eval.decision import Decision
from app.kb.loader import all_surface_forms, get_by_id

# Categories where the right answer is to link NOTHING new (used for over-correction).
KEEP_CATEGORIES = {"control", "out_of_kb", "real_speech", "unfamiliar_near_match"}
EQUIVALENT_WORDS = {"doctor": "dr", "saint": "st", "shri": "sri", "father": "fr"}


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

@dataclass
class Count:
    """A rate with its raw counts, printed like "7/12 = 58%"."""

    hits: int = 0
    total: int = 0

    def add(self, hit: bool) -> None:
        self.total += 1
        self.hits += int(hit)

    @property
    def rate(self) -> float | None:
        return self.hits / self.total if self.total else None

    def __str__(self) -> str:
        return f"{self.hits}/{self.total} = {self.rate:.0%}" if self.total else "0/0 = n/a"

    def to_dict(self) -> dict:
        return {"hits": self.hits, "total": self.total, "rate": self.rate}


def norm_words(text: str) -> list[str]:
    """Lower-case words, punctuation removed, "doctor" == "Dr.". Used for every text comparison."""
    tokens = re.sub(r"[^\w ]+", " ", text.lower().replace("'", "")).split()
    return [EQUIVALENT_WORDS.get(t, t) for t in tokens]


def contains_words(haystack: list[str], needle: list[str]) -> bool:
    """Is the word sequence `needle` in `haystack`? Allows a possessive "s" on the last word
    ("Venkataramana's" -> "venkataramanas")."""
    n = len(needle)
    for i in range(len(haystack) - n + 1):
        window = haystack[i:i + n]
        if window[:-1] == needle[:-1] and window[-1] in (needle[-1], needle[-1] + "s"):
            return True
    return False


_FORMS: dict[tuple, list[str]] | None = None


def kb_ids_in_text(text: str) -> set[str]:
    """Which KB entities are named in a text (by canonical name or alias, whole words only)."""
    global _FORMS
    if _FORMS is None:
        _FORMS = {}
        for form, ids in all_surface_forms().items():
            _FORMS.setdefault(tuple(norm_words(form)), []).extend(ids)
    words = norm_words(text)
    found: set[str] = set()
    max_len = max(len(k) for k in _FORMS)
    for i in range(len(words)):
        for n in range(1, min(max_len, len(words) - i) + 1):
            found.update(_FORMS.get(tuple(words[i:i + n]), []))
    return found


def expected_links(gt) -> set[str]:
    """KB ids the ground truth says the clip really refers to (entities + resolved references)."""
    ids = {s.entity_id for s in getattr(gt, "entities", []) if s.entity_id}
    ids |= {r.resolved_entity_id for r in getattr(gt, "references", []) if r.resolved_entity_id}
    return ids


def acceptable(gt) -> set[str]:
    return {gt.expected_behaviour, *getattr(gt, "also_acceptable", [])}


def effective_target(d: Decision) -> str | None:
    """The entity the system actually ACTS on. A clarify decision acts on nobody (yet)."""
    if d.behaviour == "clarify" or d.action.type != "remind":
        return None
    return d.action.target_entity_id


def linked_ids(d: Decision) -> set[str]:
    """Entities the decision links to (resolved entities + the action target)."""
    ids = {e.resolved_entity_id for e in d.entities if e.resolved_entity_id}
    if (t := effective_target(d)) is not None:
        ids.add(t)
    if d.behaviour != "clarify" and d.action.place_entity_id:
        ids.add(d.action.place_entity_id)
    return ids


# ---------------------------------------------------------------------------
# Per-clip checks (each returns None when the clip doesn't count for that metric)
# ---------------------------------------------------------------------------

def over_corrected(gt, text: str, decision: Decision | None = None) -> bool | None:
    """On keep-type clips: did a KB entity appear that wasn't actually said?"""
    if gt.category not in KEEP_CATEGORIES:
        return None
    said = kb_ids_in_text(gt.text)  # e.g. a real speaker who genuinely says "Pune"
    appeared = kb_ids_in_text(text) | (linked_ids(decision) if decision else set())
    return bool(appeared - said)


def wrong_target(gt, d: Decision) -> bool:
    """The worst error: acting on the wrong entity, or using an id that doesn't exist."""
    if d.invalid_ids():
        return True
    target = effective_target(d)
    if target is None:
        return False
    expected = gt.expected_action.target_entity_id
    if expected is not None:
        return target != expected
    # No expected target: acting on anyone the clip doesn't actually refer to is wrong
    # (e.g. linking "Rohan" to contact Rohit, or guessing instead of asking).
    return target not in expected_links(gt)


def expected_places(gt) -> set[str]:
    """KB places in the clip other than the action target (any of them is an acceptable place)."""
    target = gt.expected_action.target_entity_id
    return {s.entity_id for s in gt.entities if s.entity_id and s.type == "place" and s.entity_id != target}


def action_exact(gt, d: Decision) -> bool | None:
    """Right Remind: right target AND right place. Only clips that expect a targeted action."""
    exp = gt.expected_action
    if exp.type == "none" or exp.target_entity_id is None or gt.expected_behaviour == "clarify":
        return None
    if effective_target(d) != exp.target_entity_id:
        return False
    places = expected_places(gt)
    return d.action.place_entity_id in places if places else d.action.place_entity_id is None


def time_ok(gt, d: Decision) -> bool | None:
    if gt.expected_action.time_hhmm is None or gt.expected_behaviour == "clarify":
        return None
    return d.behaviour != "clarify" and d.action.time == gt.expected_action.time_hhmm


def candidates_ok(gt, d: Decision) -> bool | None:
    """When the system rightly asks, are the right people offered? (At least 2 of the expected
    candidates, or all of them if fewer than 2 were expected; no outsiders.)"""
    if gt.expected_behaviour != "clarify" or d.behaviour != "clarify":
        return None
    exp, got = set(gt.candidate_ids), set(d.clarify_candidates)
    return len(exp & got) >= min(2, len(exp)) and got <= exp


def reference_ok(gt, d: Decision) -> bool | None:
    """Personal references ("my doctor", "Amma"): every one resolved right (or rightly asked about)."""
    refs = getattr(gt, "references", [])
    if not refs:
        return None
    resolved = {e.resolved_entity_id for e in d.entities if e.resolved_entity_id}
    if (t := effective_target(d)) is not None:
        resolved.add(t)
    for r in refs:
        if r.resolved_entity_id is not None:
            if r.resolved_entity_id not in resolved:
                return False
        else:  # ambiguous: the right answer is to ask, offering only real candidates
            if d.behaviour != "clarify" or not d.clarify_candidates or not set(d.clarify_candidates) <= set(gt.candidate_ids):
                return False
    return True


# ---------------------------------------------------------------------------
# Aggregate metrics over many clips
# ---------------------------------------------------------------------------

def transcript_metrics(items: list[tuple]) -> dict:
    """items: [(ground_truth, transcript_text, decision_or_None)]."""
    entity_acc, over = Count(), Count()
    refs, hyps = [], []
    for gt, text, decision in items:
        hyp = norm_words(text)
        for span in getattr(gt, "entities", []):
            if span.entity_id:  # only KB names are scored here
                entity_acc.add(contains_words(hyp, norm_words(span.surface)))
        if (o := over_corrected(gt, text, decision)) is not None:
            over.add(o)
        ref = " ".join(norm_words(gt.text))
        if ref:
            refs.append(ref)
            hyps.append(" ".join(hyp))
    out = {"entity_accuracy": entity_acc, "over_correction_rate": over}
    if refs:
        w = jiwer.process_words(refs, hyps)
        errors = w.substitutions + w.deletions + w.insertions
        words = w.hits + w.substitutions + w.deletions
        out["wer"] = Count(errors, words)  # "errors/reference words = WER"
    else:
        out["wer"] = Count()
    return out


def decision_metrics(items: list[tuple]) -> dict:
    """items: [(ground_truth, decision)]. Real-speech clips only count for the keep checks."""
    m = {k: Count() for k in ("behaviour_accuracy", "exact_action_target_accuracy", "time_accuracy",
                               "wrong_target_rate", "unnecessary_question_rate", "missed_clarification_rate",
                               "clarify_candidates_ok", "reference_resolution_accuracy", "no_llm_rate")}
    latencies, costs = [], []
    for gt, d in items:
        exp_ok = acceptable(gt)
        m["behaviour_accuracy"].add(d.behaviour in exp_ok)
        m["wrong_target_rate"].add(wrong_target(gt, d) if gt.category != "real_speech" else bool(d.invalid_ids()))
        if "clarify" not in exp_ok:
            m["unnecessary_question_rate"].add(d.behaviour == "clarify")
        if gt.expected_behaviour == "clarify":
            m["missed_clarification_rate"].add(d.behaviour != "clarify")
        for key, check in (("exact_action_target_accuracy", action_exact), ("time_accuracy", time_ok),
                           ("clarify_candidates_ok", candidates_ok),
                           ("reference_resolution_accuracy", reference_ok)):
            if gt.category != "real_speech" and (r := check(gt, d)) is not None:
                m[key].add(r)
        m["no_llm_rate"].add(not d.used_llm)
        latencies.append(d.latency_ms)
        costs.append(d.cost_usd)
    m["latency_ms_mean"] = round(statistics.mean(latencies), 1) if latencies else None
    m["latency_ms_median"] = round(statistics.median(latencies), 1) if latencies else None
    m["cost_usd_mean"] = round(statistics.mean(costs), 6) if costs else None
    return m


# ---------------------------------------------------------------------------
# Per-clip outcome, for win / tie / loss
# ---------------------------------------------------------------------------

# Higher is better. The order says which mistakes are worse.
OUTCOME_LEVEL = {"wrong_target": 0, "over_corrected": 0, "missed_clarification": 1,
                 "unnecessary_question": 2, "wrong_behaviour": 2, "wrong_action": 2,
                 "entity_miss": 2, "ok": 3}


def clip_outcome(gt, text: str, decision: Decision | None = None) -> str:
    """One label for how a system did on one clip (the worst problem found)."""
    problems = []
    if decision is not None and gt.category != "real_speech" and wrong_target(gt, decision):
        problems.append("wrong_target")
    if over_corrected(gt, text, decision):
        problems.append("over_corrected")
    if decision is not None:
        exp_ok = acceptable(gt)
        if gt.expected_behaviour == "clarify" and decision.behaviour != "clarify":
            problems.append("missed_clarification")
        if decision.behaviour == "clarify" and "clarify" not in exp_ok:
            problems.append("unnecessary_question")
        if decision.behaviour not in exp_ok:
            problems.append("wrong_behaviour")
        if gt.category != "real_speech" and action_exact(gt, decision) is False:
            problems.append("wrong_action")
    hyp = norm_words(text)
    if any(s.entity_id and not contains_words(hyp, norm_words(s.surface)) for s in getattr(gt, "entities", [])):
        problems.append("entity_miss")
    return min(problems, key=OUTCOME_LEVEL.get) if problems else "ok"


def compare(outcome_a: str, outcome_b: str) -> str:
    """'win' if system A did better than B on this clip, 'loss' if worse, else 'tie'."""
    a, b = OUTCOME_LEVEL[outcome_a], OUTCOME_LEVEL[outcome_b]
    return "win" if a > b else "loss" if a < b else "tie"
