"""
scripts/show_errors.py — shows where baseline speech-to-text got KB names wrong.

WHAT: For every baseline results file it checks each KB entity in the reference sentence
      (e.g. "Kukatpally") and asks: does it appear exactly in the transcript? (Case and punctuation
      are ignored, and "doctor" counts as "Dr.".) It prints:
        1. a summary per results file: how many KB names were missed
        2. a table for one file (default: plain / phone): reference vs what was heard, grouped by type
        3. the 5 most "dramatic" mistakes, the ones that changed the most (e.g. "cook at Polly")
WHY:  A quick, readable look at the problem before the proper metrics in Module 5.
      The dramatic examples are what you show a mentor or judge in 10 seconds.

Run from the project root:
    python scripts/show_errors.py
    python scripts/show_errors.py --variant hints --audio clean
"""

import argparse
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.stt.baseline import RESULTS_DIR, results_path  # noqa: E402
from app.testset.validate import load_testset  # noqa: E402

# Spoken forms that are the same thing written differently.
EQUIVALENT_WORDS = {"doctor": "dr", "saint": "st", "shri": "sri"}


def words(text: str) -> list[str]:
    """Lower-case words without punctuation, e.g. "Dr. Venkataramana's" -> ["dr", "venkataramanas"]."""
    tokens = re.sub(r"[^a-z0-9 ]+", " ", text.lower().replace("'", "")).split()
    return [EQUIVALENT_WORDS.get(t, t) for t in tokens]


def find_span(haystack: list[str], needle: list[str]) -> tuple[int, int] | None:
    """Where the word list `needle` starts and ends inside `haystack` (first match), or None."""
    for i in range(len(haystack) - len(needle) + 1):
        if haystack[i:i + len(needle)] == needle:
            return i, i + len(needle)
    # Possessives like "Venkataramana's" become "venkataramanas": allow a trailing "s" on the last word.
    for i in range(len(haystack) - len(needle) + 1):
        window = haystack[i:i + len(needle)]
        if window[:-1] == needle[:-1] and window[-1] in (needle[-1], needle[-1] + "s"):
            return i, i + len(needle)
    return None


def heard_for(reference: str, transcript: str, surface: str) -> str:
    """What the transcript contains in place of `surface`, by aligning reference and transcript words.

    SequenceMatcher lines up the two word lists (like a diff). For the reference words that
    make up the name, we collect the transcript words they were aligned with.
    """
    ref, hyp, target = words(reference), words(transcript), words(surface)
    span = find_span(ref, target)
    if span is None:
        return "?"
    start, end = span
    hyp_positions = []
    for op, r1, r2, h1, h2 in SequenceMatcher(None, ref, hyp, autojunk=False).get_opcodes():
        if r2 <= start or r1 >= end:
            continue  # this block doesn't touch the name
        if op == "equal":
            hyp_positions += [h1 + (i - r1) for i in range(max(r1, start), min(r2, end))]
        elif op == "replace":
            hyp_positions += list(range(h1, h2))
        # "delete": these reference words were simply not heard
    if not hyp_positions:
        return "(missing)"
    return " ".join(hyp[min(hyp_positions):max(hyp_positions) + 1])


def misses_in(results: dict, sentences: dict) -> list[dict]:
    """Every KB entity whose surface is NOT found in the transcript."""
    out = []
    for clip_id, rec in results["clips"].items():
        s = sentences.get(clip_id)
        if s is None:  # real-speech clips have no KB entity annotations
            continue
        hyp = words(rec["transcript"])
        for span in s.entities:
            if span.entity_id is None:
                continue  # only KB names are checked here
            if find_span(hyp, words(span.surface)) is None:
                out.append({"id": clip_id, "type": span.type, "surface": span.surface,
                            "heard": heard_for(rec["reference_text"], rec["transcript"], span.surface),
                            "reference": rec["reference_text"], "transcript": rec["transcript"]})
    return out


def drama(miss: dict) -> float:
    """How different the heard text is from the real name: 0 = identical, higher = more dramatic.
    Splitting one name into several English words ("cook at Polly") scores extra."""
    if miss["heard"] in ("?", "(missing)"):
        return 0.0
    a, b = "".join(words(miss["surface"])), "".join(words(miss["heard"]))
    word_change = abs(len(words(miss["surface"])) - len(words(miss["heard"])))
    return (1 - SequenceMatcher(None, a, b).ratio()) + 0.25 * word_change


def main() -> int:
    # Transcripts can contain non-Latin script (e.g. Telugu). Some Windows terminals can't print it,
    # so replace unprintable characters instead of crashing. Saved files keep the real text.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Show KB names that baseline speech-to-text got wrong.")
    parser.add_argument("--variant", default="plain", choices=["plain", "hints"])
    parser.add_argument("--audio", default="phone", choices=["clean", "phone"])
    parser.add_argument("--model", default=settings.transcription_model)
    args = parser.parse_args()

    sentences = {s.id: s for s in load_testset()}
    files = sorted(RESULTS_DIR.glob("baseline_*.json"))
    if not files:
        print("No results yet. Run: python scripts/run_baseline.py")
        return 1

    # 1. Summary per results file.
    print("Missed KB names per results file (exact match, ignoring case/punctuation):\n")
    all_misses = {}
    for f in files:
        results = json.loads(f.read_text(encoding="utf-8"))
        misses = misses_in(results, sentences)
        all_misses[f.stem] = misses
        total = sum(sum(sp.entity_id is not None for sp in sentences[c].entities)
                    for c in results["clips"] if c in sentences)
        if total:
            print(f"  {f.stem:<52} {len(misses):>4} / {total:<4} missed ({len(misses) / total:.0%})")
        else:
            print(f"  {f.stem:<52} (no KB names: real speech)")

    # 2. Detail table for one file, grouped by entity type.
    chosen = results_path(args.variant, args.audio, args.model).stem
    misses = all_misses.get(chosen, [])
    print(f"\nDetail: {chosen}")
    for entity_type in ("person", "place", "business"):
        rows = [m for m in misses if m["type"] == entity_type]
        print(f"\n  {entity_type.upper()}S missed: {len(rows)}")
        for m in rows:
            print(f"    {m['id']}  {m['surface']:<30} -> {m['heard']}")

    # 3. The 5 most dramatic mistakes in the PLAIN baseline (one per name, any audio kind).
    print("\n5 most dramatic mistakes (plain speech-to-text):\n")
    plain = [dict(m, file=k) for k, ms in all_misses.items() if k.startswith("baseline_plain") for m in ms]
    seen, top = set(), []
    for m in sorted(plain, key=drama, reverse=True):
        if m["surface"] not in seen and drama(m) > 0:
            seen.add(m["surface"])
            top.append(m)
        if len(top) == 5:
            break
    for n, m in enumerate(top, 1):
        audio = m["file"].split("_")[2]
        print(f"  {n}. \"{m['surface']}\"  ->  \"{m['heard']}\"   ({m['id']}, {audio} audio)")
        print(f"       said : {m['reference']}")
        print(f"       heard: {m['transcript']}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
