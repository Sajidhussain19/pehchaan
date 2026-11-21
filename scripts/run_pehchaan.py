"""
scripts/run_pehchaan.py — runs Pehchaan (d) over the clips and saves its Decisions.

WHAT: For each clip it takes the SAME input as baseline (c): the baseline-(a) transcript plus who is
      talking, runs app.decide.pehchaan.resolve(), and saves the Decision in
      data/results/pehchaan_{audio}_{VERSION}.json (read automatically by scripts/evaluate.py).
      Clips already saved are skipped unless --fresh. LLM answers are cached separately, so even
      --fresh costs $0 for spans the LLM has already judged.
WHY:  Produces Pehchaan's outputs for the evaluation. Default split is dev; test needs --final.

Run from the project root:
    python scripts/run_pehchaan.py --limit 5
    python scripts/run_pehchaan.py --audio clean phone real --fresh
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.decide.config import VERSION  # noqa: E402
from app.decide.llm_fallback import PRICE_INPUT, PRICE_OUTPUT  # noqa: E402
from app.decide.pehchaan import resolve  # noqa: E402
from app.eval.runs import decision_clips, decisions_path, load_decisions, save_decisions, todo_clips  # noqa: E402

SYSTEM = "pehchaan"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Run Pehchaan's decision layer over the clips.")
    parser.add_argument("--split", choices=["dev", "test", "all"], default="dev")
    parser.add_argument("--audio", nargs="+", choices=["clean", "phone", "real"], default=["clean", "phone", "real"])
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--fresh", action="store_true", help="recompute every clip (LLM answers stay cached)")
    parser.add_argument("--final", action="store_true", help="required for the held-out test split")
    args = parser.parse_args()
    if args.split in ("test", "all") and not args.final:
        print("[STOP] The test split is held out. Add --final only when producing final numbers.")
        return 1

    jobs, n = [], 0
    for audio in args.audio:
        clips = decision_clips(audio, args.split)
        clips = clips[: args.limit] if args.limit else clips
        path = decisions_path(SYSTEM, audio, VERSION)
        store = {"meta": {}, "clips": {}} if args.fresh else load_decisions(path)
        todo = clips if args.fresh else todo_clips(clips, store)
        jobs.append((audio, todo, path, store))
        n += len(todo)
        print(f"  {audio:<6} {len(clips):>4} clips, {len(todo):>4} to run")
    # Upper-bound estimate: if EVERY clip needed one small LLM call (~600 tokens in, ~80 out).
    print(f"Estimated cost (upper bound, if every clip used the LLM): ~${n * (600 * PRICE_INPUT + 80 * PRICE_OUTPUT):.3f}")

    spent, llm_clips = 0.0, 0
    for audio, todo, path, store in jobs:
        store["meta"] = {"system": SYSTEM, "audio": audio, "version": VERSION}
        for clip in todo:
            d = resolve(clip["heard"], clip["direction"], clip["caller_contact_id"], clip_id=clip["id"])
            store["clips"][clip["id"]] = d.model_dump()
            spent += d.cost_usd
            llm_clips += d.used_llm
            print(f"  {audio:<6} {clip['id']}  {d.behaviour:<8} llm={'Y' if d.used_llm else '-'} "
                  f"target={d.action.target_entity_id}  {d.output_transcript[:55]}")
        save_decisions(path, store)
    print(f"\n[OK] {n} clips, {llm_clips} used the LLM, cost of LLM calls ~${spent:.4f} "
          f"(cached answers are re-counted at their original cost).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
