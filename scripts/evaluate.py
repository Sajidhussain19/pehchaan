"""
scripts/evaluate.py — scores every system on the same clips and writes a report.

WHAT: Loads the outputs of each system:
        a        = plain speech-to-text (Module 4)
        b        = speech-to-text with name hints (Module 4)
        c        = strong LLM baseline: one GPT-4o-mini call with the full personal context (Module 5)
        pehchaan = our system (Modules 6-8; used automatically once its results exist)
      and scores them with app/eval/metrics.py: overall, per audio kind (clean / phone / real) and
      per category, always with raw counts. It also compares two systems clip by clip
      (default: c vs pehchaan, or c vs b until Pehchaan exists;
      a text-only system is compared on text only) and counts wins / ties / losses.
      Writes data/results/report_{split}_{audio}.md and .json (the final held-out run over all audio:
      data/results/report_test_FINAL.md and .json).

HELD-OUT RULE: the default split is dev. Scoring the test split requires --final, prints a warning
      and appends a line to data/results/test_runs.log, so every look at the test split is on record.
WHY:  One script, one scoring rule for every system, so comparisons are fair and repeatable.

Run from the project root:
    python scripts/evaluate.py                         # dev split, all audio kinds
    python scripts/evaluate.py --audio phone --compare b c
    python scripts/evaluate.py --split test --final --compare pehchaan c   # ONLY for final reported numbers
"""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.eval.metrics import clip_outcome, compare, decision_metrics, transcript_metrics  # noqa: E402
from app.eval.runs import load_decision_objects, load_transcripts  # noqa: E402
from app.stt.baseline import RESULTS_DIR  # noqa: E402
from app.testset.validate import load_realspeech, load_testset  # noqa: E402

AUDIO_KINDS = ("clean", "phone", "real")
SYSTEM_LABELS = {"a": "(a) plain STT", "b": "(b) STT + hints", "c": "(c) LLM baseline", "pehchaan": "Pehchaan",
                 "v1": "Pehchaan v1", "v2": "Pehchaan v2"}
TEST_LOG = RESULTS_DIR / "test_runs.log"

TRANSCRIPT_METRICS = ("entity_accuracy", "wer", "over_correction_rate")
DECISION_METRICS = ("behaviour_accuracy", "exact_action_target_accuracy", "time_accuracy", "wrong_target_rate",
                    "unnecessary_question_rate", "missed_clarification_rate", "clarify_candidates_ok",
                    "reference_resolution_accuracy", "no_llm_rate", "latency_ms_mean", "latency_ms_median",
                    "cost_usd_mean")


def load_system(system: str, audio: str) -> dict:
    """{clip_id: (text, decision_or_None)} for one system and audio kind ({} if not run yet)."""
    if system in ("a", "b"):
        return {cid: (t, None) for cid, t in load_transcripts("plain" if system == "a" else "hints", audio).items()}
    if system == "c":
        decisions = load_decision_objects("llm_baseline", audio, settings.chat_model)
    elif system in ("v1", "v2"):  # a specific Pehchaan version (v1 = the frozen headline system)
        decisions = load_decision_objects("pehchaan", audio, system)
    else:  # pehchaan: whatever model/version tag its results file uses
        files = sorted(RESULTS_DIR.glob(f"pehchaan_{audio}_*.json"))
        decisions = load_decision_objects("pehchaan", audio, files[-1].stem.split("_", 2)[2]) if files else {}
    return {cid: (d.output_transcript, d) for cid, d in decisions.items()}


def fmt(value) -> str:
    if value is None:
        return "-"
    return str(value)


def score(system_rows: list[tuple]) -> dict:
    """All metrics for one system on a list of (gt, text, decision) rows."""
    out = transcript_metrics(system_rows)
    decisions = [(gt, d) for gt, _, d in system_rows if d is not None]
    if decisions:
        out.update(decision_metrics(decisions))
    return out


def table(title: str, systems: list[str], scores: dict, metric_names: tuple) -> list[str]:
    """A markdown table: one row per metric, one column per system."""
    lines = [f"\n### {title}\n", "| metric | " + " | ".join(SYSTEM_LABELS[s] for s in systems) + " |",
             "|---|" + "---|" * len(systems)]
    for name in metric_names:
        cells = [fmt(scores[s].get(name)) if s in scores else "-" for s in systems]
        if any(c != "-" for c in cells):
            lines.append(f"| {name} | " + " | ".join(cells) + " |")
    return lines


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Score all systems on the same clips.")
    parser.add_argument("--split", choices=["dev", "test", "test2"], default="dev")
    parser.add_argument("--final-test2", action="store_true", help="required for the sealed test-2 split")
    parser.add_argument("--audio", choices=[*AUDIO_KINDS, "all"], default="all")
    parser.add_argument("--systems", nargs="+", default=["a", "b", "c", "pehchaan"], choices=list(SYSTEM_LABELS))
    parser.add_argument("--compare", nargs=2, metavar=("A", "B"), default=None,
                        help="two systems to compare clip by clip (default: c pehchaan, else c b)")
    parser.add_argument("--final", action="store_true", help="required for --split test")
    parser.add_argument("--out", default=None, help="report file name (without extension) instead of the default")
    parser.add_argument("--title", default=None, help="extra line under the report title (e.g. 'already seen')")
    args = parser.parse_args()

    # The held-out rules. test2 (sealed at tag test2-frozen) needs --final-test2 and is logged too.
    if args.split == "test2":
        if not args.final_test2:
            print("[STOP] test-2 is a sealed held-out set. Re-run with --final-test2 only for its one final scoring.")
            return 1
        print("[WARNING] Scoring the HELD-OUT test-2 split. Do not change anything based on these results.")
        with TEST_LOG.open("a", encoding="utf-8") as log:
            log.write(f"{datetime.now().isoformat(timespec='seconds')}  split=test2 evaluate "
                      f"systems={' '.join(args.systems)}\n")
    if args.split == "test":
        if not args.final:
            print("[STOP] The test split is held out for FINAL numbers. Re-run with --final if that's what this is.")
            return 1
        print("[WARNING] Scoring the HELD-OUT test split. Do not change anything based on these results.")
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        with TEST_LOG.open("a", encoding="utf-8") as log:
            log.write(f"{datetime.now().isoformat(timespec='seconds')}  split=test audio={args.audio} "
                      f"systems={' '.join(args.systems)}\n")

    audios = AUDIO_KINDS if args.audio == "all" else (args.audio,)
    gt = {s.id: s for s in load_testset(splits=None)}
    gt.update({c.id: c for c in load_realspeech()})

    # rows[system][audio] = [(gt, text, decision)] for clips in this split.
    rows = {s: {} for s in args.systems}
    for system in args.systems:
        for audio in audios:
            outputs = load_system(system, audio)
            rows[system][audio] = [(gt[cid], text, d) for cid, (text, d) in sorted(outputs.items())
                                   if cid in gt and gt[cid].split == args.split]
    systems = [s for s in args.systems if any(rows[s][a] for a in audios)]
    missing = [s for s in args.systems if s not in systems]

    report = {"split": args.split, "audio": args.audio, "systems": systems, "overall": {}, "per_audio": {},
              "per_category": {}, "comparison": None}
    md = [f"# Pehchaan evaluation: {args.split} split, audio = {args.audio}",
          f"\nGenerated {datetime.now().isoformat(timespec='seconds')}. Systems: "
          + ", ".join(SYSTEM_LABELS[s] for s in systems)
          + (f". Not available yet: {', '.join(SYSTEM_LABELS[s] for s in missing)}." if missing else "."),
          "\nEvery number is shown with raw counts. A clarify decision takes no action until the user answers."]
    if args.title:
        md.insert(1, f"\n**{args.title}**")
        report["note"] = args.title

    # 1. Overall (all chosen audio kinds together).
    overall = {s: score([r for a in audios for r in rows[s][a]]) for s in systems}
    md += table("Overall: transcript metrics", systems, overall, TRANSCRIPT_METRICS)
    md += table("Overall: decision metrics (systems that make decisions)", systems, overall, DECISION_METRICS)
    report["overall"] = {s: {k: (v.to_dict() if hasattr(v, "to_dict") else v) for k, v in m.items()}
                         for s, m in overall.items()}

    # 2. Per audio kind.
    for audio in audios:
        per = {s: score(rows[s][audio]) for s in systems if rows[s][audio]}
        if not per:
            continue
        md += table(f"Audio = {audio}", list(per), per, TRANSCRIPT_METRICS + DECISION_METRICS[:8])
        report["per_audio"][audio] = {s: {k: (v.to_dict() if hasattr(v, "to_dict") else v) for k, v in m.items()}
                                      for s, m in per.items()}

    # 3. Per category (all audio kinds together).
    categories = sorted({r[0].category for s in systems for a in audios for r in rows[s][a]})
    for cat in categories:
        per = {s: score([r for a in audios for r in rows[s][a] if r[0].category == cat]) for s in systems}
        per = {s: m for s, m in per.items() if m["wer"].total or m.get("behaviour_accuracy")}
        md += table(f"Category = {cat}", list(per), per, TRANSCRIPT_METRICS + DECISION_METRICS[:8])
        report["per_category"][cat] = {s: {k: (v.to_dict() if hasattr(v, "to_dict") else v) for k, v in m.items()}
                                       for s, m in per.items()}

    # 4. Clip-by-clip win / tie / loss between two systems.
    pair = args.compare or (["c", "pehchaan"] if "pehchaan" in systems else ["c", "b"])
    if all(p in systems for p in pair):
        a_sys, b_sys = pair
        tally, details = Counter(), []
        for audio in audios:
            a_rows = {r[0].id: r for r in rows[a_sys][audio]}
            b_rows = {r[0].id: r for r in rows[b_sys][audio]}
            for cid in sorted(a_rows.keys() & b_rows.keys()):
                ga, ta, da = a_rows[cid]
                _, tb, db = b_rows[cid]
                # Same lens for both: if either system only outputs text, judge both on text only.
                if da is None or db is None:
                    da = db = None
                oa, ob = clip_outcome(ga, ta, da), clip_outcome(ga, tb, db)
                result = compare(oa, ob)
                tally[result] += 1
                if result != "tie":
                    details.append({"clip": cid, "audio": audio, "category": ga.category, "result": result,
                                    a_sys: oa, b_sys: ob, "said": ga.text, f"{a_sys}_text": ta, f"{b_sys}_text": tb})
        md += [f"\n## Clip by clip: {SYSTEM_LABELS[a_sys]} vs {SYSTEM_LABELS[b_sys]}\n",
               f"**{SYSTEM_LABELS[a_sys]} wins {tally['win']}, ties {tally['tie']}, loses {tally['loss']}** "
               f"(of {sum(tally.values())} clips; win = {SYSTEM_LABELS[a_sys]} did better).\n",
               f"| clip | audio | category | result | {a_sys} outcome | {b_sys} outcome | said |", "|---|---|---|---|---|---|---|"]
        md += [f"| {d['clip']} | {d['audio']} | {d['category']} | {d['result']} | {d[a_sys]} | {d[b_sys]} | {d['said'][:60]} |"
               for d in details]
        report["comparison"] = {"a": a_sys, "b": b_sys, "counts": dict(tally), "clips": details}

    # The one final held-out report gets a name that can't be confused with a dev report.
    name = (f"report_{args.split}_FINAL" if args.split in ("test", "test2") and args.audio == "all"
            else f"report_{args.split}_{args.audio}")
    if args.out:
        name = args.out  # e.g. v2 on the ORIGINAL test set (already seen): a clearly different file name
    out = RESULTS_DIR / name
    out.with_suffix(".md").write_text("\n".join(md) + "\n", encoding="utf-8")
    out.with_suffix(".json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\n".join(md[:2]))
    print("\n".join(table("Overall", systems, overall, TRANSCRIPT_METRICS + DECISION_METRICS)))
    if report["comparison"]:
        c = report["comparison"]
        print(f"\nClip by clip {c['a']} vs {c['b']}: {c['counts']}")
    print(f"\n[OK] Report: {out.with_suffix('.md').relative_to(RESULTS_DIR.parent.parent).as_posix()} (+ .json)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
