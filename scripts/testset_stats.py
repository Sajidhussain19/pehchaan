"""
scripts/testset_stats.py — prints a friendly summary of the test set and its audio.

WHAT: Loads and validates sentences.json, then prints counts by split, category, direction,
      expected behaviour, entity type and entity difficulty, plus total audio minutes from
      manifest.json (if the audio has been built).
WHY:  One quick look shows the test set is balanced and honest (plenty of non-correction cases,
      every category in both splits). It also gives numbers for the README and the pitch.

Run from the project root:
    python scripts/testset_stats.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

# Make the project root importable when this file runs as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.kb.loader import get_by_id  # noqa: E402
from app.testset.validate import (  # noqa: E402
    TESTSET_PATH,
    TestsetValidationError,
    load_testset,
    validate_testset,
)

MANIFEST_PATH = TESTSET_PATH.parent / "manifest.json"


def show(title: str, counter: Counter) -> None:
    """Print a Counter as a small aligned table, biggest first."""
    print(f"\n{title}")
    for key, count in counter.most_common():
        print(f"  {str(key):<18} {count:>4}")


def main() -> int:
    # Validation first: stats about a broken answer key would be misleading.
    try:
        sentences = load_testset()
        validate_testset(sentences)
    except (TestsetValidationError, ValueError) as err:
        print(f"[ERROR] {err}")
        return 1

    print("=" * 50)
    print(f" Pehchaan test set: {len(sentences)} sentences")
    print("=" * 50)

    show("By split:", Counter(s.split for s in sentences))
    show("By category:", Counter(s.category for s in sentences))
    show("By direction:", Counter(s.direction for s in sentences))
    show("By expected behaviour:", Counter(s.expected_behaviour for s in sentences))

    # Entity-level counts. Unlinked names (out_of_kb etc.) have no KB difficulty,
    # so they are counted as "not in KB".
    spans = [span for s in sentences for span in s.entities]
    show("Entity mentions by type:", Counter(span.type for span in spans))
    show("Entity mentions by difficulty:", Counter(
        get_by_id(span.entity_id).difficulty if span.entity_id else "not in KB" for span in spans
    ))

    # Personal references ("my doctor", "Amma"): how each one is meant to be resolved.
    refs = [r for s in sentences for r in s.references]
    show("Personal references by resolution reason:", Counter(r.resolution_reason for r in refs))

    # Audio totals, if build_audio.py has been run.
    if MANIFEST_PATH.exists():
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        minutes = sum(m["duration_seconds"] for m in manifest) / 60
        print(f"\nAudio: {len(manifest)} clips, {minutes:.1f} minutes "
              f"(each clip has a clean and a phone-quality version)")
        show("Clips by voice:", Counter(m["voice"] for m in manifest))
    else:
        print("\nAudio: not built yet (run python scripts/build_audio.py)")

    print("\n[OK] Test set validated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
