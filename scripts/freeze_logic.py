"""
scripts/freeze_logic.py — records a fingerprint of Pehchaan's decision logic (the "freeze").

WHAT: Computes a SHA-256 hash of every file that decides what Pehchaan outputs:
      the matching code (app/match/), the decision code (app/decide/), the word lists they read
      (data/lexicon/) and the base knowledge base (data/kb/contacts|places|businesses.json).
      It saves them in data/results/frozen_logic.json. tests/test_freeze.py recomputes the hashes on
      every `pytest` run and FAILS if any frozen file has changed.
WHY:  We evaluate on the held-out test split ONCE. If the logic changed after that run, the reported
      numbers would describe a system that no longer exists. The freeze makes such a change loud:
      it needs the developer's explicit approval, a repeated final run, and a note in README.

Run from the project root (only when a change has been APPROVED):
    python scripts/freeze_logic.py            # re-record the fingerprint after an approved change
"""

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FROZEN_PATH = ROOT / "data" / "results" / "frozen_logic.json"
# Everything that can change a Pehchaan decision on the default contact book.
FROZEN_GLOBS = ("app/match/*.py", "app/decide/*.py", "data/lexicon/*",
                "data/kb/contacts.json", "data/kb/places.json", "data/kb/businesses.json")


def fingerprints() -> dict[str, str]:
    """{relative path: sha256 of its content}. Line endings are normalised first, so a Windows
    checkout (CRLF) and a Linux one (LF) give the same hash for the same code."""
    out = {}
    for pattern in FROZEN_GLOBS:
        for path in sorted(ROOT.glob(pattern)):
            if path.is_file():
                data = path.read_bytes().replace(b"\r\n", b"\n")
                out[path.relative_to(ROOT).as_posix()] = hashlib.sha256(data).hexdigest()
    return out


def main() -> int:
    record = {
        "_about": "Fingerprint of Pehchaan's decision logic, recorded before the final held-out run. "
                  "tests/test_freeze.py fails if any of these files change. Changing them needs explicit "
                  "approval, a repeated final run (--final) and a disclosure in README.",
        "recorded_at": datetime.now().isoformat(timespec="seconds"),
        "files": fingerprints(),
    }
    FROZEN_PATH.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] Froze {len(record['files'])} files -> {FROZEN_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
