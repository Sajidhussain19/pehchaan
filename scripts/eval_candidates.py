"""
scripts/eval_candidates.py — how good are the candidates? DEV split only.

WHAT: Runs the matcher on every DEV clip's baseline-(a) transcript (clean, phone and real speech) and reports:
        - recall@1 / recall@3: for each ground-truth KB entity, is it the top / in the top 3
          candidates of some span?
        - reference recall: for "my doctor"-style references, is the right entity among the candidates?
        - false alarms: on clips where nothing should be linked (control, out_of_kb,
          unfamiliar_near_match, real_speech), spans whose best candidate scores >= HIGH_CONFIDENCE
          (or any reference span). These are the over-correction risks for Module 8.
        - high-confidence wrong candidates on in-KB clips (a wrong-target risk)
        - per category and audio kind, with raw counts; the 10 worst misses and 10 worst false alarms
        - speed (ms per sentence)
      --tune: grid-searches the weights in app/match/config.py and prints before vs after.
WHY:  Module 8 can only pick the right entity if it's among the candidates, and must not be
      tempted by confident candidates on clips that contain no KB names. The test split is never used.

Run from the project root:
    python scripts/eval_candidates.py
    python scripts/eval_candidates.py --tune
"""

import argparse
import itertools
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.eval.metrics import Count, KEEP_CATEGORIES, contains_words, expected_links, kb_ids_in_text, norm_words  # noqa: E402
from app.eval.runs import load_transcripts  # noqa: E402
from app.match.candidates import find_candidates  # noqa: E402
from app.match.config import DEFAULT, HIGH_CONFIDENCE, INITIAL, MatchWeights  # noqa: E402
from app.testset.validate import load_realspeech, load_testset  # noqa: E402

SPLIT = "dev"  # never "test": tuning on test would make the final numbers dishonest


def dev_clips() -> list[tuple]:
    """[(ground_truth, audio, transcript)] for every dev clip and audio kind."""
    rows = []
    sentences = [s for s in load_testset() if s.split == SPLIT]
    for audio in ("clean", "phone"):
        heard = load_transcripts("plain", audio)
        rows += [(s, audio, heard[s.id]) for s in sentences if s.id in heard]
    heard = load_transcripts("plain", "real")
    rows += [(c, "real", heard[c.id]) for c in load_realspeech() if c.split == SPLIT and c.id in heard]
    return rows


def evaluate(weights: MatchWeights, rows: list[tuple]) -> dict:
    stats = {"r1": Count(), "r3": Count(), "mis_r1": Count(), "mis_r3": Count(), "ref": Count(),
             "fa_clips": Count(), "fa_spans": 0,
             "wrong_high": Count(), "margins": [], "keep_max": [], "by": defaultdict(lambda: {"r1": Count(), "r3": Count(), "fa": Count()}),
             "misses": [], "alarms": [], "ms": []}
    for gt, audio, text in rows:
        start = time.perf_counter()
        spans = find_candidates(text, weights)
        stats["ms"].append((time.perf_counter() - start) * 1000)
        groups = [stats["by"][("all", audio)], stats["by"][(gt.category, "all")]]

        # Recall: for each true KB entity, its best rank among all spans' candidates.
        for span_gt in getattr(gt, "entities", []):
            if not span_gt.entity_id:
                continue
            ranks = [i for s in spans for i, c in enumerate(s.candidates, 1) if c.entity_id == span_gt.entity_id]
            rank = min(ranks) if ranks else None
            # Separation: how far the right entity scores above the runner-up in its span.
            for s in spans:
                if s.kind == "name" and s.candidates[0].entity_id == span_gt.entity_id:
                    stats["margins"].append(s.margin)
                    break
            for target in (stats, *groups):
                target["r1"].add(rank == 1)
                target["r3"].add(rank is not None and rank <= 3)
            # The interesting subset: names speech-to-text got WRONG (not spelled right in the transcript).
            if not contains_words(norm_words(text), norm_words(span_gt.surface)):
                stats["mis_r1"].add(rank == 1)
                stats["mis_r3"].add(rank is not None and rank <= 3)
            if rank is None or rank > 3:
                stats["misses"].append((gt.id, audio, span_gt.surface, rank, text))
        for ref in getattr(gt, "references", []):
            if ref.resolved_entity_id:
                stats["ref"].add(any(c.entity_id == ref.resolved_entity_id for s in spans for c in s.candidates))

        # False alarms: confident candidates where nothing (new) should be linked.
        if gt.category in KEEP_CATEGORIES:
            said = kb_ids_in_text(gt.text)
            # How tempting is this keep-type clip? Its highest (wrong) candidate score.
            stats["keep_max"].append(max((s.candidates[0].score for s in spans if s.kind == "name"
                                          and s.candidates[0].entity_id not in said), default=0.0))
            alarms = [s for s in spans if s.candidates[0].entity_id not in said
                      and (s.kind == "reference" or s.candidates[0].score >= HIGH_CONFIDENCE)]
            for target in (stats["fa_clips"], *(g["fa"] for g in groups)):
                target.add(bool(alarms))
            stats["fa_spans"] += len(alarms)
            stats["alarms"] += [(s.candidates[0].score, gt.id, audio, s.heard_text, s.candidates[0].name, text)
                                for s in alarms]
        elif gt.category in ("in_kb", "reference", "stale_default"):
            # (Ambiguous / context-mismatch clips are left out: there the right candidate IS proposed,
            # and deciding to ask or keep is Module 8's job, not a candidate error.)
            links = expected_links(gt)
            for s in spans:
                if s.kind == "name" and s.candidates[0].score >= HIGH_CONFIDENCE:
                    stats["wrong_high"].add(s.candidates[0].entity_id not in links)
    return stats


def separation(stats: dict) -> float:
    """Mean margin of correct top candidates minus mean best score on keep-type clips (higher = safer)."""
    margin = statistics.mean(stats["margins"]) if stats["margins"] else 0.0
    tempt = statistics.mean(stats["keep_max"]) if stats["keep_max"] else 0.0
    return margin - tempt


def summary(stats: dict) -> str:
    return (f"separation {separation(stats):+.3f} (correct margin "
            f"{statistics.mean(stats['margins'] or [0]):.2f}, keep-clip best score {statistics.mean(stats['keep_max'] or [0]):.2f}) | "
            f"recall@1 {stats['r1']} | recall@3 {stats['r3']} | MISHEARD names: recall@1 {stats['mis_r1']}, "
            f"recall@3 {stats['mis_r3']} | references {stats['ref']} | "
            f"false-alarm clips {stats['fa_clips']} ({stats['fa_spans']} spans) | "
            f"high-confidence wrong on in-KB clips {stats['wrong_high']}")


def report(stats: dict, title: str) -> None:
    print(f"\n=== {title} ===\n{summary(stats)}")
    print(f"speed: mean {statistics.mean(stats['ms']):.1f} ms, max {max(stats['ms']):.1f} ms per sentence")
    print("\nBy audio / category:            recall@1        recall@3        false-alarm clips")
    for (cat, audio), g in sorted(stats["by"].items()):
        label = f"audio={audio}" if cat == "all" else f"category={cat}"
        print(f"  {label:<30} {str(g['r1']):<15} {str(g['r3']):<15} {g['fa']}")
    print("\nWorst 10 misses (true entity not in top 3):")
    for cid, audio, surface, rank, text in stats["misses"][:10]:
        print(f"  {cid} {audio:<5} {surface:<26} rank={rank}  heard: {text[:70]}")
    print("\nWorst 10 false alarms (confident candidate on a keep-type clip):")
    for score, cid, audio, heard, name, text in sorted(stats["alarms"], reverse=True)[:10]:
        print(f"  {cid} {audio:<5} {score:.2f} \"{heard}\" -> {name}   ({text[:55]})")


def tune(rows: list[tuple], before: dict) -> MatchWeights:
    """Grid search. Goal: highest recall@3 (all names, then misheard names), without MORE
    false-alarm clips than before; ties broken by misheard recall@1, fewer false alarms, and
    finally SEPARATION (right answers stand out more; keep-type clips look less tempting)."""
    grid = {"w_fuzzy": [0.25, 0.4, 0.55], "length_penalty": [0.2, 0.35, 0.5],
            "common_penalty": [0.15, 0.25, 0.4], "type_bonus": [0.0, 0.08, 0.15], "min_span_score": [0.5, 0.6]}
    best, best_key = None, None
    names = list(grid)
    for values in itertools.product(*grid.values()):
        params = dict(zip(names, values))
        w = INITIAL.model_copy(update={**params, "w_phonetic": 1 - params["w_fuzzy"]})
        s = evaluate(w, rows)
        if s["fa_clips"].hits > before["fa_clips"].hits:
            continue  # never trade more over-correction risk for recall
        key = (s["r3"].hits, s["mis_r3"].hits, s["mis_r1"].hits, -s["fa_clips"].hits, -s["fa_spans"],
               -s["wrong_high"].hits, round(separation(s), 3))
        if best_key is None or key > best_key:
            best, best_key = w, key
    return best


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Candidate quality on the DEV split.")
    parser.add_argument("--tune", action="store_true", help="grid-search the weights (dev only)")
    args = parser.parse_args()

    rows = dev_clips()
    find_candidates("warm up")
    print(f"Dev clips: {len(rows)} (clean + phone + real). HIGH_CONFIDENCE = {HIGH_CONFIDENCE}")
    if args.tune:
        before = evaluate(DEFAULT, rows)  # the weights currently in use
        report(before, "BEFORE tuning (current DEFAULT weights)")
        best = tune(rows, before)
        after = evaluate(best, rows)
        report(after, "AFTER tuning (best grid weights)")
        changed = {k: (getattr(DEFAULT, k), v) for k, v in best.model_dump().items() if getattr(DEFAULT, k) != v}
        print(f"\nChanged weights (current -> tuned): {changed}")
        print("Copy these into TUNED in app/match/config.py.")
    else:
        report(evaluate(DEFAULT, rows), "Current weights (DEFAULT)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
