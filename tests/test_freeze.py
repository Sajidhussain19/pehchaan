"""
tests/test_freeze.py — guards the decision-logic freeze (Module 9, Step 0).

WHAT: Recomputes the fingerprint of app/match/, app/decide/, data/lexicon/ and the base KB, and compares
      it with data/results/frozen_logic.json (written by scripts/freeze_logic.py).
WHY:  The held-out test numbers are only honest if the system that produced them is the system we ship.
      If this test fails, the logic changed after the freeze: get explicit approval, repeat the final run
      with --final, disclose the change in README, and only then re-record with scripts/freeze_logic.py.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from freeze_logic import FROZEN_PATH, fingerprints  # noqa: E402


def test_decision_logic_is_unchanged_since_the_freeze():
    frozen = json.loads(FROZEN_PATH.read_text(encoding="utf-8"))["files"]
    now = fingerprints()
    changed = sorted(p for p in frozen.keys() & now.keys() if frozen[p] != now[p])
    added, removed = sorted(now.keys() - frozen.keys()), sorted(frozen.keys() - now.keys())
    assert not (changed or added or removed), (
        "Decision logic changed after the freeze. This needs explicit approval, a repeated final run "
        f"(--final) and a README disclosure.\n changed={changed}\n added={added}\n removed={removed}")
