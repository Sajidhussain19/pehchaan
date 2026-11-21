"""
app/eval/runs.py — where each system's outputs live, and how to load them for scoring.

WHAT: - decision_clips(audio, split): the inputs a resolver system (baseline (c), later Pehchaan) gets
        per clip: the baseline-(a) transcript plus call direction and caller.
      - decisions_path / load_decisions / save_decisions: the cache files of Decisions, keyed by
        system + audio + model, then by clip id.
      - load_transcripts(variant, audio): baseline (a)/(b) transcripts from Module 4.
      - add_audio_argument / chosen_audios: ONE shared "--audio" option for every runner script, so
        "--audio clean phone real" and "--audio clean --audio phone" both mean the same thing everywhere.
WHY:  Keeps file layout in ONE place, so the runner scripts and evaluate.py agree, and so
      re-running never pays twice for a clip that is already done.
"""

import argparse
from pathlib import Path

from app.eval.decision import Decision
from app.stt.baseline import AUDIO_KINDS, RESULTS_DIR, load_results, results_path, save_results
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
        items = [(s.id, s.split, s.direction, s.caller_contact_id) for s in load_testset(splits=None)]
    # "all" = dev + test, as before; the sealed test-2 split only when asked for by name (behind --final-test2).
    return [{"id": cid, "split": sp, "direction": d, "caller_contact_id": caller, "heard": heard[cid]}
            for cid, sp, d, caller in items
            if ((split == "all" and sp != "test2") or sp == split) and cid in heard]


def load_decision_objects(system: str, audio: str, model: str) -> dict[str, Decision]:
    """{clip_id: Decision} for one system/audio/model ({} if not run yet)."""
    store = load_decisions(decisions_path(system, audio, model))
    return {cid: Decision.model_validate(d) for cid, d in store["clips"].items()}


TEST_RUNS_LOG = RESULTS_DIR / "test_runs.log"


def held_out_gate(args: argparse.Namespace, what: str) -> bool:
    """The held-out rules for every runner. Returns False (after printing [STOP]) if the run is not allowed.

    test   -> needs --final (the original held-out set, final-eval-v1)
    test2  -> needs --final-test2 (the second held-out set, frozen at tag test2-frozen BEFORE v2 was run on it)
    Every allowed run on test2 appends a line to data/results/test_runs.log, so each look is on record.
    """
    if args.split in ("test", "all") and not getattr(args, "final", False):
        print("[STOP] The test split is held out. Add --final only when producing final numbers.")
        return False
    if args.split == "test2":
        if not getattr(args, "final_test2", False):
            print("[STOP] test-2 is a sealed held-out set. Add --final-test2 only for the one final test-2 run.")
            return False
        from datetime import datetime
        TEST_RUNS_LOG.parent.mkdir(parents=True, exist_ok=True)
        with TEST_RUNS_LOG.open("a", encoding="utf-8") as log:
            log.write(f"{datetime.now().isoformat(timespec='seconds')}  split=test2 {what}\n")
    return True


def add_audio_argument(parser: argparse.ArgumentParser, default: tuple[str, ...]) -> None:
    """Add the shared --audio option to a runner script.

    nargs="+" accepts several values after one flag ("--audio clean phone"), and action="extend" also
    collects repeated flags ("--audio clean --audio phone"). Before this, one runner silently kept only
    the LAST value, so "--audio clean --audio phone" ran phone alone. The default is applied in
    chosen_audios(), because argparse would EXTEND a default list instead of replacing it.
    """
    parser.add_argument("--audio", nargs="+", action="extend", choices=[*AUDIO_KINDS, "all"], default=None,
                        help=f"one or more of {', '.join(AUDIO_KINDS)} or all (default: {' '.join(default)})")
    parser.set_defaults(audio_default=default)


def chosen_audios(args: argparse.Namespace) -> list[str]:
    """The audio kinds to run, in a fixed order, without duplicates ("all" = every kind)."""
    values = args.audio or list(args.audio_default)
    if "all" in values:
        return list(AUDIO_KINDS)
    return [a for a in AUDIO_KINDS if a in values]
