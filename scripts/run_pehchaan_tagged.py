"""
scripts/run_pehchaan_tagged.py — runs an OLDER, tagged version of Pehchaan (e.g. v1 = final-eval-v1.1) on clips.

WHAT: Checks out the decision code of a git tag into a temporary git worktree, runs THAT code's resolve() on the
      same inputs every system gets (baseline (a) transcript + call direction + caller), and saves the Decisions
      into data/results/pehchaan_{audio}_{version}.json (adding to what is there). The worktree is removed after.
WHY:  To compare v1 and v2 fairly on the new held-out test-2, v1 must be the EXACT code that produced the
      headline numbers, not "today's code with some switches off". A git tag is that exact code.

Run from the project root:
    python scripts/run_pehchaan_tagged.py --tag final-eval-v1.1 --version v1 --split test2 --final-test2
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import PROJECT_ROOT, settings  # noqa: E402
from app.eval.runs import (add_audio_argument, chosen_audios, decision_clips, decisions_path,  # noqa: E402
                           held_out_gate, load_decisions, save_decisions)

# Runs INSIDE the worktree, so `app` is the tagged version's code. Reads clips as JSON, prints Decisions as JSON.
CHILD = r"""
import json, sys
from app.decide.pehchaan import resolve
clips = json.loads(sys.stdin.read())
out = {}
for c in clips:
    d = resolve(c["heard"], c["direction"], c["caller_contact_id"], clip_id=c["id"], preferences=[])
    out[c["id"]] = d.model_dump()
sys.stdout.write(json.dumps(out))
"""


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Run a tagged older version of Pehchaan on clips.")
    parser.add_argument("--tag", required=True, help="git tag with the decision code, e.g. final-eval-v1.1")
    parser.add_argument("--version", required=True, help="results file label, e.g. v1")
    parser.add_argument("--split", choices=["dev", "test", "test2"], default="dev")
    parser.add_argument("--final", action="store_true")
    parser.add_argument("--final-test2", action="store_true")
    add_audio_argument(parser, default=("clean", "phone"))
    args = parser.parse_args()
    if not held_out_gate(args, f"pehchaan {args.version} (tag {args.tag})"):
        return 1

    # The worktree has no .env, so hand the OpenAI key to the child through its environment (never printed,
    # never written to disk). Without it the old code's LLM fallback fails safe ("kept as heard"), which would
    # silently make the old version look worse than it is. (This happened once; that run was discarded.)
    env = os.environ.copy()
    if settings.openai_api_key is not None:
        env["OPENAI_API_KEY"] = settings.openai_api_key.get_secret_value()
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp) / "tree"
        subprocess.run(["git", "worktree", "add", "--detach", str(tree), args.tag], cwd=PROJECT_ROOT, check=True,
                       capture_output=True)
        try:
            for audio in chosen_audios(args):
                clips = decision_clips(audio, args.split)
                print(f"  {audio:<6} {len(clips)} clips with the code of tag {args.tag}")
                run = subprocess.run([sys.executable, "-c", CHILD], cwd=tree, input=json.dumps(clips),
                                     capture_output=True, text=True, encoding="utf-8", env=env)
                if run.returncode != 0:
                    print(run.stderr[-2000:])
                    return 1
                decisions = json.loads(run.stdout)
                failed = [cid for cid, d in decisions.items() if any("LLM unavailable" in e["reason"] for e in d["entities"])]
                if failed:  # never save a run where the old version could not reach its LLM
                    print(f"[ERROR] the LLM fallback failed on {len(failed)} clips ({failed[:5]}); nothing saved.")
                    return 1
                path = decisions_path("pehchaan", audio, args.version)
                store = load_decisions(path)
                store["clips"].update(decisions)
                store.setdefault("meta", {}).update({"system": "pehchaan", "version": args.version, "code_tag": args.tag})
                save_decisions(path, store)
                n_llm = sum(d["used_llm"] for d in decisions.values())
                cost = sum(d["cost_usd"] for d in decisions.values())
                print(f"  {audio:<6} saved {len(decisions)} decisions ({n_llm} used the LLM, ~${cost:.4f})")
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(tree)], cwd=PROJECT_ROOT, capture_output=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
