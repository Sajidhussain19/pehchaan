"""
scripts/inspect_candidates.py — shows what the matcher finds in a transcript (no LLM, no decisions).

WHAT: For any text, or a clip id (using its baseline-(a) transcript), prints every span:
        heard text -> top 3 candidates with score, sound and spelling similarity, margin and reasons.
      --dramatic runs it on the 5 most dramatic speech-to-text mistakes from Module 4.
WHY:  To SEE why a candidate scored as it did. This is the quickest way to debug or explain matching.

Run from the project root:
    python scripts/inspect_candidates.py "Call Aunt Johnny and ask if tuition is on"
    python scripts/inspect_candidates.py --clip s066 --audio phone
    python scripts/inspect_candidates.py --dramatic
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.eval.runs import load_transcripts  # noqa: E402
from app.match.candidates import find_candidates, timed_find_candidates  # noqa: E402
from app.testset.validate import load_testset  # noqa: E402

# The 5 most dramatic plain-STT mistakes found by scripts/show_errors.py in Module 4.
DRAMATIC = [("s025", "phone"), ("s099", "clean"), ("s100", "clean"), ("s030", "clean"), ("s060", "clean")]


def show(text: str, said: str | None = None) -> None:
    spans, ms = timed_find_candidates(text)
    if said:
        print(f"  said : {said}")
    print(f"  heard: {text}    ({ms:.1f} ms)")
    if not spans:
        print("    (no spans)")
    for s in spans:
        hint = f", hint={s.type_hint}" if s.type_hint else ""
        print(f"    [{s.kind}{hint}] \"{s.heard_text}\"  margin {s.margin:.2f}")
        for i, c in enumerate(s.candidates, 1):
            detail = f"sound {c.phonetic:.2f}, spelling {c.fuzzy:.2f}" if s.kind == "name" else ""
            print(f"       {i}. {c.name:<28} score {c.score:.2f}  {detail}")
            if i == 1:
                print(f"          why: {'; '.join(c.reasons)}")
    print()


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Show candidate spans for a transcript.")
    parser.add_argument("text", nargs="?", help="any transcript text")
    parser.add_argument("--clip", help="a clip id, e.g. s025 (uses its plain speech-to-text transcript)")
    parser.add_argument("--audio", default="phone", choices=["clean", "phone", "real"])
    parser.add_argument("--dramatic", action="store_true", help="the 5 dramatic Module 4 mistakes")
    args = parser.parse_args()

    find_candidates("warm up")  # build the index once, so timings show the real per-sentence cost
    said = {s.id: s.text for s in load_testset()}
    if args.dramatic:
        for clip, audio in DRAMATIC:
            print(f"== {clip} ({audio} audio)")
            show(load_transcripts("plain", audio)[clip], said[clip])
    elif args.clip:
        show(load_transcripts("plain", args.audio)[args.clip], said.get(args.clip))
    elif args.text:
        show(args.text)
    else:
        parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
