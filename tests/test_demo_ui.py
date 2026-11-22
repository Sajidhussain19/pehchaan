"""Regression checks for the demo wording and JavaScript event handlers."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_demo_wording_matches_the_saved_clip_groups():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    script = (ROOT / "DEMO_SCRIPT.md").read_text(encoding="utf-8")
    footer = (ROOT / "web/index.html").read_text(encoding="utf-8")
    phrase = "speech AI on every voice request (demo clips replay their saved transcripts)"
    assert phrase in readme and phrase in script
    assert "original test set (seen before v2), followed by dev clip s101 (used for tuning)" in readme
    assert "held-out test-2 examples" in readme and "approximate $2/day cap" in readme
    assert ("220 held-out clips; evaluated once after the decision logic was frozen "
            "(a disclosed repeat after one approved change gave identical scores)") in footer


@pytest.mark.skipif(not shutil.which("node"), reason="browser unit tests require Node.js")
def test_browser_event_handlers():
    subprocess.run(["node", "--test", str(ROOT / "tests/web_ui.test.cjs")], check=True)
