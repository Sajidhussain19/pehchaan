"""
app/decide/config.py — the thresholds the decision layer uses (tuned on DEV only).

WHAT: For a name span whose best candidate scores `score` and leads the runner-up by `margin`:
        score >= HIGH and margin >= MARGIN           -> resolve, no LLM
        score >= LOW  and margin <  MARGIN           -> close call: try clue tie-break, else ask
                                                        (or the LLM if the top score isn't HIGH)
        LOW <= score < HIGH (clear leader)           -> the small LLM fallback decides
        score < LOW                                  -> keep as heard
      VERSION names the results file (data/results/pehchaan_{audio}_{VERSION}.json).
WHY:  One place for the numbers that trade "fix more names" against "never act on the wrong one".
"""

from pydantic import BaseModel


class DecideConfig(BaseModel):
    high: float = 0.80  # confident enough to resolve without asking anyone
    # The leader must beat the runner-up by this much to be "clearly" the one. Round 0 (dev): 0.12 let
    # "Call Harshit at 5" resolve with a 0.16 lead over Harshil; 0.20 turns it into a close call.
    margin: float = 0.20
    low: float = 0.65  # below this, a candidate is too weak to even ask about: keep as heard
    # v2: an everyday word ("roju", "aaj") may only become a name if it matches almost perfectly AND sits in a
    # strong name position ("call ...", "Dr. ...", "to <place>").
    very_high: float = 0.95
    llm_model: str = "gpt-4o-mini"


DEFAULT = DecideConfig()
VERSION = "v2"  # v1 = final-eval-v1/v1.1 (frozen headline); v2 = over-correction fixes
