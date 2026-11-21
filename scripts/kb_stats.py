"""
scripts/kb_stats.py — prints a friendly summary of the knowledge base.

WHAT: Loads the KB (which also validates it), then prints counts by type, by language of
      origin and by difficulty, the total number of aliases, and 10 example "hard" entities.
WHY:  A quick look at the numbers shows whether the KB is balanced: enough hard cases,
      enough languages. It is also a handy slide for judges ("327 entities, 13 language origins").

Run from the project root:
    python scripts/kb_stats.py
"""

import sys
from collections import Counter
from pathlib import Path

# Make the project root importable when this file runs as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.kb.loader import KBValidationError, all_surface_forms, load_kb  # noqa: E402


def print_counter(title: str, counter: Counter) -> None:
    """Print a Counter as a small aligned table, biggest first."""
    print(f"\n{title}")
    for key, count in counter.most_common():
        print(f"  {key:<12} {count:>4}")


def main() -> int:
    # Loading the KB also runs every validation check. If the data is broken,
    # show the clear list of problems instead of a long stack trace.
    try:
        kb = load_kb()
    except KBValidationError as err:
        print(f"[ERROR] {err}")
        return 1

    print("=" * 50)
    print(f" Pehchaan knowledge base: {len(kb)} entities")
    print("=" * 50)

    print_counter("By type:", Counter(e.type for e in kb))
    print_counter("By language origin:", Counter(e.language_origin for e in kb))
    print_counter("By difficulty:", Counter(e.difficulty for e in kb))

    total_aliases = sum(len(e.aliases) for e in kb)
    print(f"\nAliases (alternate spellings): {total_aliases}")
    print(f"Surface forms (names + aliases, unique): {len(all_surface_forms())}")

    # Show 10 hard entities: 4 people, 3 places, 3 businesses, so the examples stay varied.
    # [::5] takes every 5th hard entity of that type, spreading picks across languages.
    print("\n10 example HARD entities:")
    examples = []
    for entity_type, how_many in (("person", 4), ("place", 3), ("business", 3)):
        hard = [e for e in kb if e.difficulty == "hard" and e.type == entity_type]
        examples.extend(hard[::5][:how_many])
    for e in examples:
        aliases = ", ".join(e.aliases[:3])
        print(f"  [{e.type:<8}] {e.name:<28} ({e.language_origin}) aka: {aliases}")

    print("\n[OK] Knowledge base loaded and validated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
