"""
scripts/run_baseline.py — runs baselines (a) plain and (b) name-hints speech-to-text over the clips.

WHAT: For each chosen variant (plain / hints) and audio kind (clean / phone / real), it transcribes
      every clip and saves data/results/baseline_{variant}_{audio}_{model}.json with, per clip:
      reference text, transcript, latency_ms and estimated cost. Clips already in a results file
      are skipped, so re-running is free. It prints the estimated cost BEFORE spending anything.
WHY:  These are the "before" numbers. Module 5 scores them, and the stronger baselines and
      Pehchaan are compared against them.

Run from the project root:
    python scripts/run_baseline.py --limit 3                  # 3 clips per combination (cheap check)
    python scripts/run_baseline.py                            # dev split, clean + phone + real
    python scripts/run_baseline.py --split test --final --audio phone --variant hints --model gpt-4o-transcribe
    python scripts/run_baseline.py --split test --final --audio clean phone real   # several audio kinds at once
"""

import argparse
import sys
from pathlib import Path

# Make the project root importable when this file runs as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.eval.runs import add_audio_argument, chosen_audios  # noqa: E402
from app.stt.baseline import (  # noqa: E402
    AUDIO_KINDS,
    VARIANTS,
    clips_to_do,
    load_clips,
    load_results,
    results_path,
    run_clips,
)
from app.stt.hints import build_hint_prompt  # noqa: E402
from app.stt.transcribe import SUPPORTED_MODELS, estimate_cost, transcribe  # noqa: E402


def main() -> int:
    # Transcripts can contain non-Latin script (e.g. Telugu). Some Windows terminals can't print it,
    # so replace unprintable characters instead of crashing. Saved files keep the real text.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Run baseline speech-to-text (plain and with name hints).")
    parser.add_argument("--split", choices=["dev", "test", "all"], default="dev")
    add_audio_argument(parser, default=AUDIO_KINDS)  # e.g. --audio clean phone real
    parser.add_argument("--variant", choices=[*VARIANTS, "all"], default="all")
    parser.add_argument("--limit", type=int, default=None, help="only the first N clips per combination")
    parser.add_argument("--model", choices=SUPPORTED_MODELS, default=settings.transcription_model)
    parser.add_argument("--final", action="store_true", help="required for the held-out test split")
    parser.add_argument("--yes", action="store_true", help="don't ask for confirmation above $1")
    args = parser.parse_args()
    # The held-out rule, same as the other runners: the test split needs an explicit --final.
    if args.split in ("test", "all") and not args.final:
        print("[STOP] The test split is held out. Add --final only when producing final numbers.")
        return 1

    audios = chosen_audios(args)
    variants = VARIANTS if args.variant == "all" else (args.variant,)
    hint = build_hint_prompt(args.model)  # same hint prompt for every clip in variant (b)

    # Step 1: plan every (variant, audio) combination and estimate the cost before spending.
    jobs, total_estimate = [], 0.0
    for audio in audios:
        clips = load_clips(audio, args.split)[: args.limit] if args.limit else load_clips(audio, args.split)
        if not clips:
            print(f"[skip] no {audio} clips" + (" (run scripts/fetch_real_speech.py first)" if audio == "real" else ""))
            continue
        for variant in variants:
            path = results_path(variant, audio, args.model)
            results = load_results(path)
            todo = clips_to_do(clips, results)
            prompt = hint.text if variant == "hints" else None
            cost = sum(estimate_cost(c["duration_seconds"], args.model, prompt) for c in todo)
            total_estimate += cost
            jobs.append((variant, audio, clips, results, path, prompt, len(todo), cost))
            print(f"  {variant:<6} {audio:<6} {len(clips):>4} clips, {len(todo):>4} to transcribe  ~${cost:.3f}")

    print(f"\nModel: {args.model}.  Hint prompt: {hint.summary()}")
    print(f"Estimated cost of this run: ~${total_estimate:.3f}")
    if total_estimate > 1.0 and not args.yes:
        if input("Continue? [y/N] ").strip().lower() != "y":
            return 0

    # Step 2: run each combination. run_clips saves after every clip (safe to interrupt).
    spent = []  # cost estimate of every clip transcribed in THIS run (a list is thread-safe to append to)
    for variant, audio, clips, results, path, prompt, n_todo, _ in jobs:
        if n_todo == 0:
            continue
        results["meta"] = {"variant": variant, "audio": audio, "model": args.model,
                           "hint_prompt": hint.summary() if variant == "hints" else None}
        print(f"\n== {variant} / {audio}: {n_todo} clips ==")

        def show(clip, record):
            spent.append(record["cost_estimate_usd"])
            print(f"  {clip['id']}  {record['transcript'][:70]}")

        run_clips(clips, results, path, lambda p, prompt: transcribe(p, prompt=prompt, model=args.model),
                  prompt=prompt, on_done=show)

    # Step 3: what this run actually cost (estimated from audio minutes + prompt tokens).
    print(f"\n[OK] Done. {len(spent)} clips transcribed, estimated cost ~${sum(spent):.3f}")
    print("Results: data/results/baseline_{variant}_{audio}_" + args.model + ".json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
