"""
app/decide/pehchaan.py — the one function the rest of the project calls: resolve(transcript) -> Decision.

WHAT: Runs the LangGraph pipeline (app/decide/graph.py) on one transcript and returns a Decision, the
      same format as baseline (c), so evaluate.py scores both identically. `trace()` also returns the
      per-span reasoning, for debugging and the demo UI.
      `book` picks the user's contact book ("default" = the full KB used for evaluation; "A"/"B" are
      the demo books, see data/kb/books/). Every KB lookup inside the pipeline then uses that book.
WHY:  A single, simple entry point. The API (Module 9) and the scripts all use this function.
"""

import time
from functools import lru_cache

from app.decide.config import DEFAULT, DecideConfig
from app.decide.graph import build_graph
from app.eval.decision import Decision
from app.kb.loader import DEFAULT_BOOK, use_book


@lru_cache(maxsize=1)
def _graph():
    return build_graph()  # compiling the graph once is enough


def trace(transcript: str, direction: str = "outgoing", caller_contact_id: str | None = None,
          clip_id: str = "live", preferences: list | None = None, client=None,
          config: DecideConfig = DEFAULT, book: str = DEFAULT_BOOK) -> dict:
    """Run the pipeline and return the full final state (items with reasons + the Decision)."""
    with use_book(book):  # every KB lookup (and the preferences file) now uses this contact book
        return _graph().invoke({
            "transcript": transcript, "direction": direction, "caller_contact_id": caller_contact_id,
            "clip_id": clip_id, "preferences": preferences, "client": client, "config": config,
            "started": time.perf_counter(),
        })


def resolve(transcript: str, direction: str = "outgoing", caller_contact_id: str | None = None,
            clip_id: str = "live", preferences: list | None = None, client=None,
            config: DecideConfig = DEFAULT, book: str = DEFAULT_BOOK) -> Decision:
    """transcript (+ who is talking) -> Decision. `preferences=None` reads the book's saved preferences."""
    return trace(transcript, direction, caller_contact_id, clip_id, preferences, client, config, book)["decision"]
