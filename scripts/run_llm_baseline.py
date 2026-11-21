"""
scripts/run_llm_baseline.py — runs baseline (c), the strong LLM baseline, over the clips.

WHAT: For each clip it takes the baseline-(a) transcript (plain speech-to-text) for the chosen audio
      kind, calls app.baselines.llm_resolver.resolve() once, and saves the Decision in
      data/results/llm_baseline_{audio}_{model}.json. Clips already there are skipped (cache), so
      re-running is free. Prints the estimated cost first.
WHY:  Produces the decisions that scripts/evaluate.py scores against the ground truth.

Run from the project root:
    python scripts/run_llm_baseline.py --limit 3                 # dev split, clean + phone, 3 clips each
    python scripts/run_llm_baseline.py --audio clean --audio phone
    python scripts/run_llm_baseline.py --split test --final      # held-out split: only for final numbers
"""

import argparse
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.baselines.llm_resolver import estimate_cost_per_call, resolve  # noqa: E402
from app.config import settings  # noqa: E402
from app.eval.runs import decision_clips, decisions_path, load_decisions, save_decisions, todo_clips  # noqa: E402

SYSTEM = "llm_baseline"  # the name used in results files and reports


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Run baseline (c): one GPT-4o-mini call per clip.")
    parser.add_argument("--split", choices=["dev", "test", "all"], default="dev")
    parser.add_argument("--audio", choices=["clean", "phone", "real", "all"], action="append",
                        help="repeatable; default: clean and phone")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--model", default=settings.chat_model)
    parser.add_argument("--final", action="store_true", help="required to run on the held-out test split")
    args = parser.parse_args()

    if args.split in ("test", "all") and not args.final:
        print("[STOP] The test split is held out. Add --final only when producing final numbers.")
        return 1
    audios = args.audio or ["clean", "phone"]
    if "all" in audios:
        audios = ["clean", "phone", "real"]

    # Plan + cost estimate before spending anything.
    jobs, n_total = [], 0
    for audio in audios:
        clips = decision_clips(audio, args.split)
        clips = clips[: args.limit] if args.limit else clips
        path = decisions_path(SYSTEM, audio, args.model)
        store = load_decisions(path)
        todo = todo_clips(clips, store)  # cache: already-decided clips cost nothing
        n_total += len(todo)
        jobs.append((audio, todo, path, store))
        print(f"  {audio:<6} {len(clips):>4} clips, {len(todo):>4} to run")
    print(f"Model {args.model}. Estimated cost: ~${n_total * estimate_cost_per_call():.3f} "
          f"({n_total} calls x ~${estimate_cost_per_call():.4f})")

    spent, lock = [], threading.Lock()
    for audio, todo, path, store in jobs:
        store["meta"] = {"system": SYSTEM, "audio": audio, "model": args.model,
                         "input": f"baseline (a) plain transcript, {audio} audio"}

        def work(clip):
            decision = resolve(clip["id"], clip["heard"], clip["direction"], clip["caller_contact_id"],
                               model=args.model)
            with lock:  # one thread at a time updates and saves the cache file
                store["clips"][clip["id"]] = decision.model_dump()
                save_decisions(path, store)
                spent.append(decision.cost_usd)
            print(f"  {audio:<6} {clip['id']}  {decision.behaviour:<8} target={decision.action.target_entity_id}"
                  f"  {decision.output_transcript[:55]}")

        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(work, todo))

    print(f"\n[OK] {len(spent)} calls, cost ~${sum(spent):.4f}. Results: data/results/llm_baseline_*_{args.model}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
