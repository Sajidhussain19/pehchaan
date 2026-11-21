"""
app/match/phonetic.py — "does this SOUND like that?" for Indian names in English transcripts.

WHAT: normalise(text)            lower case, no punctuation, single spaces (Indian scripts transliterated)
      indian_phonetic_key(text)  a spelling-independent "sound key" using Indian-English sound rules
      metaphone_keys(text)       Double Metaphone keys (a classic English sound code), a second opinion
      phonetic_similarity(a, b)  0-1: how alike two texts sound (both keys, compared with RapidFuzz)
WHY:  Speech-to-text writes what it THINKS it heard in English words: "Thirumalai" -> "the roomer life",
      "Kukatpally" -> "cook at Polly". Spelling is wildly different, but the SOUND is close. Removing
      spaces and applying sound rules makes those two look alike, so a name can be found again.
"""

import re
from functools import lru_cache

from metaphone import doublemetaphone
from rapidfuzz import fuzz

from app.match.translit import has_indic, transliterate

# Share of the final score that comes from our Indian key (the rest from Double Metaphone).
# Our key knows Indian spellings (aa/ee, th/dh); Metaphone knows English spelling habits
# ("cook at polly" and "Kukatpally" both become KKTPL). Each catches what the other misses.
INDIAN_KEY_SHARE = 0.6


@lru_cache(maxsize=50_000)
def normalise(text: str) -> str:
    """Lower case, Indian scripts -> Latin, punctuation removed, spaces collapsed.
    "Dr. Venkataramana's" -> "dr venkataramanas"."""
    if has_indic(text):
        text = transliterate(text)
    text = re.sub(r"[^a-z0-9 ]+", " ", text.lower().replace("'", ""))
    return " ".join(text.split())


# The sound rules, applied in this order. Each says what it fixes, with an example.
_RULES = [
    # Aspirated consonants: Indian spellings add "h" that English ears drop, or vice versa.
    (r"th", "t"),   # "Thirumalai" ~ "the roomer" -> both start "t-r"; "Thakkar" ~ "Takkar"
    (r"dh", "d"),   # "Madhapur" ~ "Madapur"; "Dhillon" ~ "Dillon"
    (r"bh", "b"),   # "Bhavesh" ~ "Bavesh"; "Bhat" ~ "Bat"
    (r"ph", "f"),   # "Phadke" ~ "Fadke" ("ph" sounds "f" in English names)
    (r"kh", "k"),   # "Khader" ~ "Kader"; "Khammam" ~ "Kammam"
    (r"gh", "g"),   # "Ghatkopar" ~ "Gatkopar"; "Raghu" ~ "Ragu"
    (r"chh", "ch"),  # "Chhatrapati" ~ "Chatrapati"
    (r"ck", "k"),   # "cock" -> "kok" (so "Cockatiel" ~ "Kakatiya")
    (r"c(?!h)", "k"),  # hard "c": "cook at" -> "kook at" ~ "Kukat"
    (r"q", "k"),    # "Qureshi" ~ "Kureshi"; "Qadir" ~ "Kadir"
    (r"x", "ks"),
    (r"w", "v"),    # Indian English doesn't separate w/v: "Warrier" ~ "Varrier", "Swathi" ~ "Svathi"
    (r"z", "j"),    # "Zehra" ~ "Jehra"; "Imtiaz" ~ "Imtiaj" (z is often said as j)
    (r"sh", "s"),   # "Sharma" ~ "Sarma"; "Subhashis" ~ "Subhasis" (s/sh merge)
    # Long vowels written double, and English vowel spellings for the same sound.
    (r"aa", "a"),   # "Raaju" ~ "Raju"; "Ameerpet" vs "Amirpet" handled by ee/ii below
    (r"ee|ii", "i"),  # "Keerthi" ~ "Kirthi"; transliterated "ravii" ~ "ravi"
    (r"oo|uu", "u"),  # "the roomer" ~ "tirumalai" (both "ru"); "Pooja" ~ "Puja"
    (r"y$", "i"),   # final y sounds "i": "Johnny" ~ "Joni", "Kukatpally" ~ "Kukatpalli"
    # A silent "h" after a vowel ("johnny", "subah") is not pronounced.
    (r"(?<=[aeiou])h(?![aeiou])", ""),
    (r"h$", ""),    # trailing h: "Shah" ~ "Sha", "Rukhsana Begum" etc.
    # Double letters sound single: "Kukatpally" ~ "Kukatpaly", "Thakkar" ~ "Thakar".
    (r"(.)\1+", r"\1"),
]
_COMPILED_RULES = [(re.compile(pattern), replacement) for pattern, replacement in _RULES]


@lru_cache(maxsize=50_000)
def indian_phonetic_key(text: str) -> str:
    """Spaces removed (names get split into English words), then the sound rules.
    Example: "the roomer life" -> "theroomerlife" -> "teroomerlife" -> "terumerlife"
             "Thirumalai"      -> "thirumalai"    -> "tirumalai"
    Those two keys are now far closer than the original spellings."""
    key = normalise(text).replace(" ", "")
    for pattern, replacement in _COMPILED_RULES:
        key = pattern.sub(replacement, key)
    return key


@lru_cache(maxsize=50_000)
def metaphone_keys(text: str) -> tuple[str, ...]:
    """Double Metaphone codes (primary, and an alternative if any) for the text without spaces.
    "cook at polly" -> ("KKTPL",), "Kukatpally" -> ("KKTPL",): identical."""
    joined = normalise(text).replace(" ", "")
    return tuple(k for k in doublemetaphone(joined) if k)


def metaphone_similarity(a: str, b: str) -> float:
    """Best RapidFuzz ratio between any Metaphone code of a and any of b (0-1)."""
    keys_a, keys_b = metaphone_keys(a), metaphone_keys(b)
    if not keys_a or not keys_b:
        return 0.0
    return max(fuzz.ratio(x, y) for x in keys_a for y in keys_b) / 100


def phonetic_similarity(a: str, b: str) -> float:
    """How alike two texts SOUND, 0-1: a blend of our Indian key and Double Metaphone."""
    indian = fuzz.ratio(indian_phonetic_key(a), indian_phonetic_key(b)) / 100
    return INDIAN_KEY_SHARE * indian + (1 - INDIAN_KEY_SHARE) * metaphone_similarity(a, b)
