"""
app/match/config.py — the scoring weights for candidate matching, in one place.

WHAT: `MatchWeights` holds every number that shapes a candidate's score (0-1):

        base  = (w_phonetic * phonetic + w_fuzzy * fuzzy) / (w_phonetic + w_fuzzy)
        score = base
                - length_penalty  * (1 - length_ratio)   # "a" vs "Abids": very different lengths
                + type_bonus      if the context hint agrees with the entity type
                - type_penalty    if it disagrees
                - common_penalty                          # if every word is common English and
                                                          # the text isn't exactly this KB name
                + capital_bonus   if the words were capitalised in the transcript
        clipped to [0, 1]

      INITIAL = hand-picked starting values. TUNED = values chosen by scripts/eval_candidates.py --tune
      on the DEV split (never the test split). DEFAULT is what the code uses.
WHY:  Weights are a design decision we must be able to explain and change in one place. Keeping
      the "before" values lets us show what tuning changed.
"""

from pydantic import BaseModel


class MatchWeights(BaseModel):
    w_phonetic: float = 0.6  # how much SOUND matters
    w_fuzzy: float = 0.4  # how much SPELLING matters
    length_penalty: float = 0.3  # punishes length mismatches (short words matching long names)
    type_bonus: float = 0.08  # context says "person" and the entity is a person, etc.
    type_penalty: float = 0.05  # context says "place" but the entity is a person, etc.
    common_penalty: float = 0.25  # protects ordinary English ("lucky", "rose", "a bit")
    capital_bonus: float = 0.03  # speech-to-text capitalises words it thinks are names
    min_span_score: float = 0.55  # name spans whose best candidate scores below this are dropped
    top_k: int = 3  # candidates kept per span
    shortlist: int = 25  # forms pre-selected by a fast fuzzy search before full scoring
    max_tokens: int = 4  # longest span, in words


INITIAL = MatchWeights()

# Chosen by `python scripts/eval_candidates.py --tune` on the DEV split (see LEARNING.md, Modules 6+7).
# Recall was already 100% on dev, so the grid was decided by "separation": right candidates stand
# further above the runner-up (margin 0.26 -> 0.33), and clips with no KB names look less tempting
# (their best wrong candidate 0.56 -> 0.42). Recall and false alarms did not change.
#
# RETUNE (Module 8, Step 0): 21 hard dev-only sentences were added. On the bigger dev set the
# grid moved weight back to SOUND (0.45 -> 0.75): one new misheard name ("Cyclomar" for "Sai Kumar")
# was only found that way. recall@3 97/98 -> 98/98, misheard recall@3 39/40 -> 40/40, false alarms
# unchanged (2/34). Cost: separation got worse (keep-clip best wrong score 0.42 -> 0.53), which
# Module 8's guards (type check, unfamiliar-name guard, margins) must absorb.
TUNED = MatchWeights(
    w_phonetic=0.75,  # retune: 0.45 -> 0.75 (sound finds badly misheard names)
    w_fuzzy=0.25,  # retune: 0.55 -> 0.25
    length_penalty=0.5,  # was 0.3: short English words matching long names are punished harder
    type_bonus=0.0,  # was 0.08: the person/place hints didn't help on dev, so they no longer add score
    common_penalty=0.25,  # retune: back to 0.25 (protects ordinary English when sound weighs more)
    min_span_score=0.6,  # was 0.55: drops weak, noisy spans before Module 8 ever sees them
)

DEFAULT = TUNED

# A candidate scoring at or above this is "high confidence": Module 8 may act on it.
# eval_candidates.py counts such candidates on keep-type clips as FALSE ALARMS.
HIGH_CONFIDENCE = 0.80
