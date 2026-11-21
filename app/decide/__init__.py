"""
app.decide package — Pehchaan's decision layer (Module 8).

WHAT: config.py (thresholds), lexicons.py (clue words, Indian first names), llm_fallback.py (the ONE
      small LLM call for unsure cases), graph.py (the LangGraph pipeline: one node per step),
      pehchaan.py (resolve(transcript) -> Decision).
WHY:  Turns Module 7's candidates into the same Decision format as baseline (c): resolve, keep or
      ask, plus a Remind action, with every step visible. Most clips need no LLM at all.
"""
