"""
app/stt/baseline.py — runs speech-to-text over many clips, with a results cache.

WHAT: `load_clips(audio)` lists the clips to transcribe (synthetic clean / phone, or real speech).
      `run_clips(...)` transcribes every clip that is NOT already in the results file, saving after
      each clip, so an interrupted run loses nothing and a re-run costs $0.
      Results live in data/results/baseline_{variant}_{audio}_{model}.json.
WHY:  Transcription costs money and time. Caching by (variant, audio, model, clip id) means we pay
      once per clip, and Module 5 can re-score the same transcripts as often as we like.
      The logic lives here (not in the script) so the tests can check the caching.
"""

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.config import PROJECT_ROOT
from app.testset.validate import TESTSET_PATH, load_realspeech, load_testset

RESULTS_DIR = PROJECT_ROOT / "data" / "results"
SYNTHETIC_MANIFEST = TESTSET_PATH.parent / "manifest.json"
VARIANTS = ("plain", "hints")
AUDIO_KINDS = ("clean", "phone", "real")


def results_path(variant: str, audio: str, model: str) -> Path:
    return RESULTS_DIR / f"baseline_{variant}_{audio}_{model}.json"


def load_clips(audio: str, split: str = "all") -> list[dict]:
    """Clips for one audio kind: [{id, split, reference_text, audio_path, duration_seconds}]."""
    if audio in ("clean", "phone"):
        manifest = json.loads(SYNTHETIC_MANIFEST.read_text(encoding="utf-8"))
        texts = {s.id: s.text for s in load_testset()}  # reference = the text we gave to TTS
        clips = [{
            "id": m["id"], "split": m["split"], "reference_text": texts[m["id"]],
            "audio_path": m[f"{audio}_path"], "duration_seconds": m["duration_seconds"],
        } for m in manifest]
    elif audio == "real":
        clips = [{
            "id": c.id, "split": c.split, "reference_text": c.text,
            "audio_path": c.audio_path, "duration_seconds": c.duration_seconds,
        } for c in load_realspeech()]  # [] until scripts/fetch_real_speech.py has been run
    else:
        raise ValueError(f"unknown audio kind {audio!r}")
    return [c for c in clips if split == "all" or c["split"] == split]


def load_results(path: Path) -> dict:
    """Existing results file, or an empty one."""
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"meta": {}, "clips": {}}


def save_results(path: Path, results: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def clips_to_do(clips: list[dict], results: dict) -> list[dict]:
    """The cache rule: a clip is skipped if this results file already has it."""
    return [c for c in clips if c["id"] not in results["clips"]]


def run_clips(clips, results, path, transcribe_fn, prompt=None, workers=4, on_done=None) -> int:
    """Transcribe every not-yet-done clip and save after each one. Returns how many were transcribed.

    A few clips run in parallel (threads), because each call mostly waits on the network.
    A lock makes sure only one thread updates and writes the results file at a time.
    """
    todo = clips_to_do(clips, results)
    lock = threading.Lock()

    def work(clip):
        out = transcribe_fn(PROJECT_ROOT / clip["audio_path"], prompt=prompt)
        record = {"reference_text": clip["reference_text"], "transcript": out["text"],
                  "latency_ms": out["latency_ms"], "cost_estimate_usd": out["cost_estimate_usd"],
                  "split": clip["split"]}
        with lock:
            results["clips"][clip["id"]] = record
            save_results(path, results)
        if on_done:
            on_done(clip, record)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        # list() re-raises the first error, if any, instead of hiding it.
        list(pool.map(work, todo))
    return len(todo)
