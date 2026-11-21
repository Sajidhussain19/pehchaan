"""
app.stt package — speech-to-text (Module 4).

WHAT: transcribe.py sends one audio file to OpenAI speech-to-text; hints.py builds the
      "name hints" prompt for baseline (b); baseline.py runs many clips with caching.
WHY:  These produce the "before" transcripts that every later number is compared against.
"""
