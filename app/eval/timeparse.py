"""
app/eval/timeparse.py — turns a spoken time phrase into a clock time "HH:MM" (or None).

WHAT: normalise_time("tomorrow at 10 AM") -> "10:00", ("8 PM tonight") -> "20:00",
      ("kal shaam saat baje") -> "19:00", ("six thirty tomorrow morning") -> "06:30".
      It returns None when there is no clock time ("Friday", "next week") or when the hour is
      AMBIGUOUS ("at 5": 5 AM or 5 PM?). We never guess.
WHY:  A reminder needs a clock time. The test set stores times as spoken; this gives one
      shared, simple rule to turn them into "HH:MM", so "time accuracy" is scored the same way
      for every system. Only clips with an unambiguous time are scored on time.
"""

import re

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    # Hindi numbers, as spoken in code-mixed sentences ("saat baje" = seven o'clock)
    "ek": 1, "do": 2, "teen": 3, "char": 4, "paanch": 5, "chhe": 6, "saat": 7, "aath": 8,
    "nau": 9, "das": 10, "gyarah": 11, "barah": 12,
}
MINUTE_WORDS = {"thirty": 30, "fifteen": 15, "forty five": 45}
# Words that tell us morning (AM) or afternoon/evening (PM) when "AM"/"PM" isn't said.
MORNING = ("morning", "subah", "breakfast")
EVENING = ("afternoon", "evening", "night", "tonight", "shaam", "raat")


def normalise_time(text: str | None) -> str | None:
    """Return "HH:MM" (24-hour clock) for an unambiguous spoken time, else None."""
    if not text:
        return None
    t = text.lower().replace(".", "")  # "8 p.m." -> "8 pm"

    # 1. Find the hour (and minutes): "8:30", "10", "six thirty", "saat baje".
    hour = minute = None
    if m := re.search(r"\b(\d{1,2}):(\d{2})\b", t):
        hour, minute = int(m.group(1)), int(m.group(2))
    elif m := re.search(r"\b(\d{1,2})\s*(am|pm)?\b(?!\s*(?:th|st|nd|rd|minutes|hours))", t):
        # A bare number like "the 10th" or "in 10 minutes" is NOT a clock time (excluded above).
        hour, minute = int(m.group(1)), 0
    else:
        for word, value in NUMBER_WORDS.items():
            if re.search(rf"\b{word}\b", t) and not re.search(rf"\bevery {word}\b", t):
                hour, minute = value, 0
                for mword, mvalue in MINUTE_WORDS.items():
                    if re.search(rf"\b{word} {mword}\b", t):
                        minute = mvalue
                break
    if hour is None or not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None

    # 2. Decide AM or PM: explicit "am"/"pm" first, then morning/evening words.
    if hour <= 12:
        if re.search(r"\bpm\b", t) or any(w in t for w in EVENING):
            hour = hour % 12 + 12
        elif re.search(r"\bam\b", t) or any(w in t for w in MORNING):
            hour = hour % 12
        elif ":" not in t:
            return None  # "at 5" with no AM/PM or time-of-day word: ambiguous, don't guess
    return f"{hour:02d}:{minute:02d}"
