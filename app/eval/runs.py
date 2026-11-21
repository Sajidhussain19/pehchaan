"""
app/eval/runs.py — where each system's outputs live, and how to load them for scoring.

WHAT: - decision_clips(audio, split): the inputs a resolver system (baseline (c), later Pehchaan) gets
        per clip: the baseline-(a) transcript plus call direction and caller.
      - decisions_path / load_decisions / save_decisions: the cache files of Decisions, keyed by
        system + audio + model, then by clip id.
      - load_transcripts(variant, audio): baseline (a)/(b) transcripts from Module 4.
WHY:  Keeps file layout in ONE place, so the runner scripts and evaluate.py agree, and so
      re-running never pays twice for a clip that is already done.
"""

from pathlib import Path

from app.eval.decision import Decision
from app.stt.baseline import RESULTS_DIR, load_results, results_path, save_results
from app.testset.validate import load_realspeech, load_testset

TRANSCRIPTION_MODEL_FOR_INPUT = "gpt-4o-mini-transcribe"  # the Module 4 transcripts we build on


def decisions_path(system: str, audio: str, model: str) -> Path:
    return RESULTS_DIR / f"{system}_{audio}_{model}.json"


def load_decisions(path: Path) -> dict:
    return load_results(path)  # same {"meta": ..., "clips": {id: ...}} layout as Module 4


def save_decisions(path: Path, store: dict) -> None:
    save_results(path, store)


def todo_clips(clips: list[dict], store: dict) -> list[dict]:
    """The cache rule: skip any clip that already has a saved decision in this store."""
    return [c for c in clips if c["id"] not in store["clips"]]


def load_transcripts(variant: str, audio: str, model: str = TRANSCRIPTION_MODEL_FOR_INPUT) -> dict:
    """{clip_id: transcript} from a Module 4 results file ({} if it doesn't exist)."""
    store = load_results(results_path(variant, audio, model))
    return {cid: rec["transcript"] for cid, rec in store["clips"].items()}


def decision_clips(audio: str, split: str = "dev") -> list[dict]:
    """Inputs for a resolver system: what speech-to-text heard (baseline (a)) + who is talking.
    Every resolver gets exactly this, so the comparison is fair."""
    heard = load_transcripts("plain", audio)
    if audio == "real":
        items = [(c.id, c.split, "outgoing", None) for c in load_realspeech()]
    else:
        items = [(s.id, s.split, s.direction, s.caller_contact_id) for s in load_testset()]
    return [{"id": cid, "split": sp, "direction": d, "caller_contact_id": caller, "heard": heard[cid]}
            for cid, sp, d, caller in items
            if (split == "all" or sp == split) and cid in heard]


def load_decision_objects(system: str, audio: str, model: str) -> dict[str, Decision]:
    """{clip_id: Decision} for one system/audio/model ({} if not run yet)."""
    store = load_decisions(decisions_path(system, audio, model))
    return {cid: Decision.model_validate(d) for cid, d in store["clips"].items()}
