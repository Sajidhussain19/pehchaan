"""
app/match/translit.py — turns Devanagari and Telugu script into rough Latin letters.

WHAT: transliterate("रवी तेजक") -> "ravi tejak", transliterate("కుకట్పల్లి") -> "kukatpalli".
      A letter-by-letter table: each consonant carries a built-in "a" unless a vowel sign or the
      "virama" (a mark meaning "no vowel") follows it. Latin text passes through unchanged.
WHY:  In Module 4, code-mixed lines like "Ravi Teja ko call karo" came back from speech-to-text
      in Devanagari ("रवी तेजक को कॉल करो"). Our KB is in Latin script, so without this step those
      names could never match. It doesn't need to be perfect, only close enough for phonetic matching.
"""

# Devanagari (Hindi) ---------------------------------------------------------
_DEV_VOWELS = {"अ": "a", "आ": "aa", "इ": "i", "ई": "ii", "उ": "u", "ऊ": "uu", "ऋ": "ri", "ए": "e",
               "ऐ": "ai", "ओ": "o", "औ": "au", "ऑ": "o", "ऍ": "e"}
_DEV_SIGNS = {"ा": "aa", "ि": "i", "ी": "ii", "ु": "u", "ू": "uu", "ृ": "ri", "े": "e", "ै": "ai",
              "ो": "o", "ौ": "au", "ॉ": "o", "ॅ": "e"}
_DEV_CONS = {"क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "n", "च": "ch", "छ": "chh", "ज": "j",
             "झ": "jh", "ञ": "n", "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n", "त": "t",
             "थ": "th", "द": "d", "ध": "dh", "न": "n", "प": "p", "फ": "ph", "ब": "b", "भ": "bh",
             "म": "m", "य": "y", "र": "r", "ल": "l", "व": "v", "श": "sh", "ष": "sh", "स": "s",
             "ह": "h", "क़": "q", "ख़": "kh", "ग़": "g", "ज़": "z", "ड़": "r", "ढ़": "rh", "फ़": "f", "ळ": "l"}
_DEV_OTHER = {"ं": "n", "ँ": "n", "ः": "h", "़": "", "।": ".", "॥": "."}
_DEV_VIRAMA = "्"

# Telugu ---------------------------------------------------------------------
_TEL_VOWELS = {"అ": "a", "ఆ": "aa", "ఇ": "i", "ఈ": "ii", "ఉ": "u", "ఊ": "uu", "ఋ": "ru", "ఎ": "e",
               "ఏ": "ee", "ఐ": "ai", "ఒ": "o", "ఓ": "oo", "ఔ": "au"}
_TEL_SIGNS = {"ా": "aa", "ి": "i", "ీ": "ii", "ు": "u", "ూ": "uu", "ృ": "ru", "ె": "e", "ే": "ee",
              "ై": "ai", "ొ": "o", "ో": "oo", "ౌ": "au"}
_TEL_CONS = {"క": "k", "ఖ": "kh", "గ": "g", "ఘ": "gh", "ఙ": "n", "చ": "ch", "ఛ": "chh", "జ": "j",
             "ఝ": "jh", "ఞ": "n", "ట": "t", "ఠ": "th", "డ": "d", "ఢ": "dh", "ణ": "n", "త": "t",
             "థ": "th", "ద": "d", "ధ": "dh", "న": "n", "ప": "p", "ఫ": "ph", "బ": "b", "భ": "bh",
             "మ": "m", "య": "y", "ర": "r", "ఱ": "r", "ల": "l", "ళ": "l", "వ": "v", "శ": "sh",
             "ష": "sh", "స": "s", "హ": "h"}
_TEL_OTHER = {"ం": "m", "ః": "h"}
_TEL_VIRAMA = "్"

SCRIPTS = [
    # (vowels, vowel signs, consonants, other marks, virama, drop final "a"?)
    # Hindi usually drops the last inherent "a" ("Ram", not "Rama"); Telugu keeps it.
    (_DEV_VOWELS, _DEV_SIGNS, _DEV_CONS, _DEV_OTHER, _DEV_VIRAMA, True),
    (_TEL_VOWELS, _TEL_SIGNS, _TEL_CONS, _TEL_OTHER, _TEL_VIRAMA, False),
]


def _script_for(ch: str):
    for script in SCRIPTS:
        vowels, signs, cons, other, virama, _ = script
        if ch in vowels or ch in signs or ch in cons or ch in other or ch == virama:
            return script
    return None


def transliterate(text: str) -> str:
    """Latin output for Devanagari/Telugu input; any other character is copied unchanged."""
    out: list[str] = []
    pending_a = False  # a consonant was just written and still "owns" an inherent "a"
    drop_final_a = False

    def flush(word_end: bool):
        nonlocal pending_a
        if pending_a and not (word_end and drop_final_a):
            out.append("a")
        pending_a = False

    for ch in text:
        script = _script_for(ch)
        if script is None:  # Latin letter, space, punctuation...
            flush(word_end=True)
            out.append(ch)
            continue
        vowels, signs, cons, other, virama, drop_final_a = script
        if ch in cons:
            flush(word_end=False)  # the previous consonant keeps its "a"
            out.append(cons[ch])
            pending_a = True
        elif ch in signs:  # a vowel sign replaces the inherent "a"
            pending_a = False
            out.append(signs[ch])
        elif ch == virama:  # explicit "no vowel"
            pending_a = False
        elif ch in vowels:
            flush(word_end=False)
            out.append(vowels[ch])
        else:  # anusvara, visarga, nukta, danda
            if ch in ("ं", "ँ", "ం"):
                flush(word_end=False)
            out.append(other[ch])
    flush(word_end=True)
    return "".join(out)


def has_indic(text: str) -> bool:
    """True if the text contains Devanagari or Telugu characters."""
    return any("ऀ" <= ch <= "ॿ" or "ఀ" <= ch <= "౿" for ch in text)
