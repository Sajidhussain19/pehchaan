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


def test_first_screen_and_scoreboard_order():
    html = (ROOT / "web/index.html").read_text(encoding="utf-8")
    assert html.count("▶ Start the 5-step doctor demo") == 3  # header and both empty cards
    assert "Waiting for input" not in html
    assert "Hear 'my doctor'. Find the right contact. Save the reminder." in html
    assert "Strong AI (GPT-4o-mini with the same contacts)" in html
    assert html.index('id="score-v2-lead"') < html.index('id="score-v2-caveat"') < html.index('id="score-v2-table"')
    assert html.index('id="score-v2-table"') < html.index("Original held-out test (v1, before the fix)")


@pytest.mark.skipif(not shutil.which("node"), reason="browser unit tests require Node.js")
def test_browser_event_handlers():
    subprocess.run(["node", "--test", str(ROOT / "tests/web_ui.test.cjs")], check=True)
