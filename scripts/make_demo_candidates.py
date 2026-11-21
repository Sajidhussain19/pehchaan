"""
scripts/make_demo_candidates.py — writes data/results/demo_candidates.md (+ .json) from the FINAL test results.

WHAT: For a short, hand-picked list of held-out test clips it pulls, straight from the saved result files:
      what was said, what speech-to-text heard, what baseline (c) did and what Pehchaan did (with reasons),
      for both the clean and the phone recording. The picks are 5 clips where Pehchaan is right and (c) is
      wrong on BOTH recordings, one per failure type, plus 1 honest Pehchaan failure.
WHY:  The demo centrepiece must be a real held-out clip where the two systems diverge, shown with the
      overall win / tie / loss counts. Generating the page from the result files (not typing it by hand)
      means the demo can't quietly drift from the reported numbers. The API (GET /api/clips) reads the JSON.

Run from the project root (after the final run):
    python scripts/make_demo_candidates.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.kb.loader import get_by_id  # noqa: E402
from app.stt.baseline import RESULTS_DIR  # noqa: E402
from app.testset.validate import load_testset  # noqa: E402

# (clip id, failure type of baseline (c), why it is a good demo). Chosen from report_test_FINAL.json:
# Pehchaan "ok" and (c) wrong on BOTH clean and phone audio, one clip per failure type.
PICKS = [
    ("s104", "missed clarification",
     "Two contacts are called Rohit/Rohith. (c) silently picks one; Pehchaan asks which one."),
    ("s140", "clue vs default",
     "\"tooth filling\" is a clue for the dentist. (c) uses the stale default (family doctor)."),
    ("s108", "type mismatch",
     "You can't book a table at a doctor. (c) maps it to a dental clinic; Pehchaan asks."),
    ("s067", "misheard name",
     "\"Padyalakshmi Jewelers\" -> Bhagyalakshmi Jewellers by sound. (c) gives up and keeps it."),
    ("s125", "family word (reference)",
     "\"Bhaiya\" in Hindi script is the user's elder brother Rajat. (c) picks a different contact."),
]
FAILURE = ("s090", "over-correction (Pehchaan's honest failure)",
           "Telugu \"ee roju\" (= today) sounds like Dr. Raju at 0.80, just above the confidence bar, so Pehchaan "
           "\"fixes\" an ordinary word into a contact's name. (c) correctly leaves it alone. This is the most common "
           "kind of Pehchaan loss on the held-out set (over-correction 11/70 vs (c) 3/70).")


def _name(entity_id):
    e = get_by_id(entity_id) if entity_id else None
    return e.name if e else None


def _did(d: dict) -> str:
    """One readable line: behaviour, target or question, and the per-entity reasons."""
    if d["behaviour"] == "clarify":
        head = "ASKS: " + " or ".join(_name(i) or i for i in d["clarify_candidates"]) + "?"
    else:
        target = _name(d["action"].get("target_entity_id"))
        head = f"{d['behaviour'].upper()}" + (f", action target = {target}" if target else ", no action target")
    reasons = "; ".join(f"\"{e['heard_text']}\" -> {_name(e.get('resolved_entity_id')) or 'kept'} ({e.get('reason', '')})"
                        for e in d.get("entities", []))
    sep = " " if head.endswith("?") else ". "
    return head + (f"{sep}{reasons}" if reasons else "")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    report = json.loads((RESULTS_DIR / "report_test_FINAL.json").read_text(encoding="utf-8"))
    outcome = {(c["clip"], c["audio"]): c for c in report["comparison"]["clips"]}
    sentences = {s.id: s for s in load_testset()}
    files = {a: {"c": json.loads((RESULTS_DIR / f"llm_baseline_{a}_gpt-4o-mini.json").read_text(encoding="utf-8"))["clips"],
                 "p": json.loads((RESULTS_DIR / f"pehchaan_{a}_v1.json").read_text(encoding="utf-8"))["clips"]}
             for a in ("clean", "phone")}

    counts = report["comparison"]["counts"]
    md = ["# Demo candidates (from the FINAL held-out test run)", "",
          f"Source: `data/results/report_test_FINAL.json`. Overall, clip by clip, Pehchaan vs (c): "
          f"**win {counts.get('win', 0)}, tie {counts.get('tie', 0)}, loss {counts.get('loss', 0)}**.", "",
          "Each clip below was picked because Pehchaan and baseline (c) diverge on **both** the clean and the phone "
          "recording. Everything is copied from the saved result files by `scripts/make_demo_candidates.py`."]
    out = []
    for i, (cid, kind, why) in enumerate([*PICKS, FAILURE], start=1):
        s = sentences[cid]
        is_failure = cid == FAILURE[0]
        md += ["", f"## {i}. {cid}: {kind}" if not is_failure else f"## Honest failure: {cid}: {kind}", "",
               f"- **Said:** \"{s.text}\"",
               f"- **Expected:** {s.expected_behaviour}"
               + (f", target {_name(s.expected_action.target_entity_id)}" if s.expected_action.target_entity_id else ""),
               f"- **Why it's a good demo:** {why}"]
        item = {"clip_id": cid, "kind": kind, "why": why, "text": s.text, "category": s.category,
                "honest_failure": is_failure, "audio": {}}
        for audio in ("clean", "phone"):
            c, p = files[audio]["c"][cid], files[audio]["p"][cid]
            res = outcome.get((cid, audio), {"result": "tie"})["result"]
            md += [f"- **{audio}** (`data/testset/audio/{audio}/{cid}.wav`), Pehchaan {res}:",
                   f"  - heard: \"{p['heard_transcript']}\"",
                   f"  - (c): {_did(c)}",
                   f"  - Pehchaan: {_did(p)}"]
            item["audio"][audio] = {"path": f"data/testset/audio/{audio}/{cid}.wav", "result": res,
                                    "heard": p["heard_transcript"], "baseline_c": _did(c), "pehchaan": _did(p)}
        out.append(item)

    (RESULTS_DIR / "demo_candidates.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (RESULTS_DIR / "demo_candidates.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n",
                                                      encoding="utf-8")
    print("\n".join(md))
    print("\n[OK] data/results/demo_candidates.md (+ .json)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
