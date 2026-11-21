"""
app.match package — candidate spans + phonetic matching (Modules 6+7). NO LLM, NO decisions.

WHAT: translit.py   Devanagari / Telugu script -> Latin letters (speech-to-text sometimes writes
                    code-mixed lines in Indian scripts)
      phonetic.py   "sounds-alike" keys and a 0-1 phonetic similarity
      config.py     the scoring weights (tuned on dev only)
      spans.py      find the parts of a transcript that might be names or personal references
      candidates.py score KB entities for each span and keep the best, non-overlapping spans
WHY:  Speech-to-text turns names into English words ("Anjani" -> "Aunt Johnny"), so we compare by
      SOUND across word boundaries. Module 8 then decides what to do with these candidates.
"""
