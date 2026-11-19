"""Hindi (Devanagari) to Hinglish (Latin/English script) transliteration.

Converts Devanagari text produced by speech-to-text models into natural, readable
Hinglish (colloquial Roman Hindi) while preserving punctuation, whitespace,
and word-level timestamps for video subtitles.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional

# Devanagari Unicode code-point range
DEVANAGARI_START = 0x0900
DEVANAGARI_END = 0x097F


def has_devanagari(text: Optional[str]) -> bool:
    """Return True if text contains any Devanagari character."""
    if not text:
        return False
    return any(DEVANAGARI_START <= ord(c) <= DEVANAGARI_END for c in text)


# ---------------------------------------------------------------------------
# High-frequency dictionary for standard, conversational Hinglish spellings
# ---------------------------------------------------------------------------
HINDI_TO_HINGLISH: Dict[str, str] = {
    # Pronouns & demonstratives
    "ये": "ye", "यह": "yeh", "वो": "wo", "वह": "woh",
    "मैं": "main", "मुझे": "mujhe", "मुझको": "mujhko", "मेरा": "mera", "मेरी": "meri", "मेरे": "mere",
    "हम": "hum", "हमें": "humein", "हमको": "humko", "हमारा": "hamara", "हमारी": "hamari", "हमारे": "hamare",
    "तुम": "tum", "तुम्हें": "tumhein", "तुम्हारा": "tumhara", "तुम्हारी": "tumhari", "तुम्हारे": "tumhare",
    "तू": "tu", "तुझे": "tujhe", "तेरा": "tera", "तेरी": "teri", "तेरे": "tere",
    "आप": "aap", "आपको": "aapko", "आपका": "aapka", "आपकी": "aapki", "आपके": "aapke",
    "इस": "is", "इसको": "isko", "इसे": "ise", "इसका": "iska", "इसकी": "iski", "इसके": "iske",
    "उस": "us", "उसको": "usko", "उसे": "use", "उसका": "uska", "उसकी": "uski", "उसके": "uske",
    "इन": "in", "इनको": "inko", "इन्हें": "inhein", "इनका": "inka", "इनकी": "inki", "इनके": "inke",
    "उन": "un", "उनको": "unko", "उन्हें": "unhein", "उनका": "unka", "उनकी": "unki", "उनके": "unke",
    "सब": "sab", "सबको": "sabko", "सभी": "sabhi",
    "कोई": "koi", "किसी": "kisi", "किसीको": "kisiko", "कुछ": "kuch",
    "कौन": "kaun", "किस": "kis", "किसे": "kise",

    # Interrogatives
    "क्या": "kya", "क्यों": "kyun", "कैसे": "kaise", "कैसा": "kaisa", "कैसी": "kaisi",
    "कब": "kab", "कहाँ": "kahan", "कहा": "kaha", "किधर": "kidhar",
    "कितना": "kitna", "कितने": "kitne", "कितनी": "kitni",

    # Locatives / Time
    "यहाँ": "yahan", "वहाँ": "wahan", "जहाँ": "jahan",
    "इधर": "idhar", "उधर": "udhar", "जिधर": "jidhar",
    "आज": "aaj", "कल": "kal", "परसों": "parson", "अब": "ab", "तब": "tab", "जब": "jab",
    "कभी": "kabhi", "हमेशा": "hamesha", "रोज": "roz", "रोज़": "roz", "फिर": "phir", "दोबारा": "dobara",

    # Auxiliary / To be
    "है": "hai", "हैं": "hain", "हो": "ho", "हूँ": "hoon", "था": "tha", "थी": "thi", "थे": "the", "थीं": "theen",
    "होगा": "hoga", "होगी": "hogi", "होंगे": "honge", "होना": "hona", "होने": "hone",
    "होती": "hoti", "होता": "hota", "होते": "hote", "होकर": "hokar",
    "रहा": "raha", "रही": "rahi", "रहे": "rahe", "रहीं": "raheen",

    # Go / Come / Become
    "गया": "gaya", "होगया": "hogaya", "गई": "gayi", "गए": "gaye", "गईं": "gayeen",
    "जा": "jaa", "जाना": "jaana", "जाओ": "jao", "जाते": "jaate", "जाता": "jaata", "जाती": "jaati",
    "आया": "aaya", "आई": "aayi", "आए": "aaye", "आ": "aa", "आना": "aana", "आओ": "aao",
    "आते": "aate", "आता": "aata", "आती": "aati", "आकर": "aakar",
    "हुआ": "hua", "हुई": "hui", "हुए": "hue",

    # Do / Say / See / Hear
    "कर": "kar", "किया": "kiya", "की": "ki", "किए": "kiye", "करना": "karna", "करो": "karo", "करें": "karein",
    "करते": "karte", "करता": "karta", "करती": "karti", "करेंगे": "karenge", "करेगा": "karega", "करेगी": "karegi",
    "बोल": "bol", "बोला": "bola", "बोली": "boli", "बोले": "bole", "बोलना": "bolna", "बोलो": "bolo",
    "देख": "dekh", "देखा": "dekha", "देखी": "dekhi", "देखे": "dekhe", "देखना": "dekhna", "देखो": "dekho",
    "देखते": "dekhte", "देखता": "dekhta", "देखती": "dekhti",
    "सुन": "sun", "सुना": "suna", "सुनी": "suni", "सुने": "sune", "सुनना": "sunna", "सुनो": "suno", "सुनते": "sunte",
    "ले": "le", "लिया": "liya", "ली": "li", "लिए": "liye", "लेना": "lena", "लो": "lo",
    "दे": "de", "दिया": "diya", "दी": "di", "दिए": "diye", "देना": "dena", "दो": "do", "देकर": "dekar",
    "जान": "jaan", "जाना": "jaana", "जानते": "jaante", "जानता": "jaanta", "जानती": "jaanti", "पता": "pata",
    "समझ": "samajh", "समझा": "samjha", "समझी": "samjhi", "समझना": "samjhna", "समझो": "samjho",
    "लग": "lag", "लगा": "laga", "लगी": "lagi", "लगे": "lage", "लगना": "lagna", "लगता": "lagta", "लगती": "lagti", "लगते": "lagte",
    "सक": "sak", "सका": "saka", "सकी": "saki", "सके": "sake", "सकता": "sakta", "सकती": "sakti", "सकते": "sakte", "सकेंगे": "sakenge",
    "चाहिए": "chahiye", "चाहता": "chahta", "चाहती": "chahti", "चाहते": "chahte",
    "मिल": "mil", "मिला": "mila", "मिली": "mili", "मिले": "mile", "मिलना": "milna", "मिलते": "milte",
    "रख": "rakh", "रखा": "rakha", "रखी": "rakhi", "रखे": "rakhe", "रखना": "rakhna", "रखो": "rakho",
    "चल": "chal", "चला": "chala", "चली": "chali", "चले": "chale", "चलना": "chalna", "चलो": "chalo", "चलते": "chalte", "चलता": "chalta",
    "रह": "rah", "रहना": "rahna", "रहो": "raho",
    "बैठ": "baith", "बैठा": "baitha", "बैठो": "baitho",
    "उठ": "uth", "उठा": "utha", "उठो": "utho",
    "पड़": "pad", "पड़ा": "pada", "पड़ी": "padi", "पड़े": "pade", "पड़ता": "padta",

    # Conjunctions & Prepositions
    "और": "aur", "या": "ya", "लेकिन": "lekin", "मगर": "magar", "पर": "par", "परंतु": "parantu",
    "क्योंकि": "kyunki", "ताकि": "taaki", "अगर": "agar", "यदि": "yadi", "तो": "to",
    "का": "ka", "की": "ki", "के": "ke", "को": "ko", "से": "se", "में": "mein", "पे": "pe", "तक": "tak",
    "साथ": "saath", "पास": "paas", "बिना": "bina", "बारे": "baare", "द्वारा": "dwara",
    "वाला": "wala", "वाली": "wali", "वाले": "wale", "वालों": "walon",

    # Common adjectives & adverbs
    "अच्छा": "achha", "अच्छी": "achhi", "अच्छे": "achhe",
    "बुरा": "bura", "बुरी": "buri", "बुरे": "bure",
    "बड़ा": "bada", "बड़ी": "badi", "बड़े": "bade",
    "छोटा": "chhota", "छोटी": "chhoti", "छोटे": "chhote",
    "बहुत": "bahut", "ज्यादा": "zyada", "कम": "kam",
    "ठीक": "theek", "सही": "sahi", "गलत": "galat",
    "नया": "naya", "नई": "nayi", "नए": "naye",
    "पुराना": "purana", "पुरानी": "purani", "पुराने": "purane",
    "पहला": "pehla", "पहली": "pehli", "पहले": "pehle",
    "दूसरा": "doosra", "दूसरी": "doosri", "दूसरे": "doosre",
    "तेज": "tez", "तेज़": "tez", "धीमे": "dheeme", "जल्दी": "jaldi", "धीरे": "dheere",
    "पूरा": "poora", "पूरी": "poori", "पूरे": "poore",
    "ज़रूरी": "zaroori", "जरूरी": "zaroori", "ज़रूरत": "zaroorat",

    # Negatives & Affirmations
    "हाँ": "haan", "हां": "haan", "नहीं": "nahi", "ना": "na", "मत": "mat",

    # Salutations & People
    "नमस्ते": "namaste", "नमस्कार": "namaskar",
    "भाई": "bhai", "भैया": "bhaiya", "यार": "yaar", "दोस्त": "dost", "दोस्तों": "dosto",
    "लोग": "log", "लोगों": "logon", "इंसान": "insaan", "आदमी": "aadmi", "बच्चा": "bachha", "बच्चे": "bachhe",
    "लड़का": "ladka", "लड़की": "ladki", "लड़के": "ladke", "लड़कियां": "ladkiyan",
    "माता": "mata", "पिता": "pita", "माँ": "maa", "पापा": "papa", "मम्मी": "mummy",

    # Common nouns & loanwords
    "बात": "baat", "बातें": "baatein", "काम": "kaam", "चीज": "cheez", "चीज़": "cheez", "चीजें": "cheezein",
    "समय": "samay", "वक्त": "waqt", "दिन": "din", "रात": "raat", "साल": "saal", "महीना": "mahina",
    "घर": "ghar", "रास्ता": "raasta", "जगह": "jagah", "दुनिया": "duniya", "देश": "desh", "भारत": "Bharat",
    "वीडियो": "video", "चैनल": "channel", "सब्सक्राइब": "subscribe", "लाइक": "like", "शेयर": "share",
    "कमेंट": "comment", "फॉलो": "follow", "गेम": "game", "गेमिंग": "gaming", "लाइव": "live",
    "फोन": "phone", "गाड़ी": "gaadi", "पैसा": "paisa", "पैसे": "paise", "रुपए": "rupaye", "रुपया": "rupaya",
    "नाम": "naam", "सवाल": "sawal", "जवाब": "jawab", "मदद": "madad", "खुश": "khush",
}

# ---------------------------------------------------------------------------
# Phonetic tables for algorithmic transliteration fallback
# ---------------------------------------------------------------------------
CONSONANTS: Dict[str, str] = {
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "ng",
    "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "ny",
    "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n",
    "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
    "य": "y", "र": "r", "ल": "l", "व": "v",
    "श": "sh", "ष": "sh", "स": "s", "ह": "h",
    "क़": "q", "ख़": "kh", "ग़": "gh", "ज़": "z", "ड़": "d", "ढ़": "dh", "फ़": "f",
    "ळ": "l",
}

VOWELS: Dict[str, str] = {
    "अ": "a", "आ": "aa", "इ": "i", "ई": "ee", "उ": "u", "ऊ": "oo",
    "ऋ": "ri", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au",
    "ऑ": "o", "ऍ": "e",
}

MATRAS: Dict[str, str] = {
    "ा": "a", "ि": "i", "ी": "i", "ु": "u", "ू": "u",
    "ृ": "ri", "े": "e", "ै": "ai", "ो": "o", "ौ": "au",
    "ॉ": "o", "ॅ": "e",
}


def _algorithmic_transliterate_word(word: str) -> str:
    """Algorithmically transliterate a single Devanagari word with schwa deletion."""
    word = unicodedata.normalize("NFC", word)
    chars = list(word)
    n = len(chars)
    i = 0
    res: List[str] = []

    while i < n:
        c = chars[i]

        # Handle nukta combinations (e.g. क + ़ = क़)
        if i + 1 < n and chars[i + 1] == "\u093c":
            comb = c + chars[i + 1]
            if comb in CONSONANTS:
                c = comb
                i += 1

        if c in CONSONANTS:
            cons = CONSONANTS[c]
            if i + 1 < n:
                nxt = chars[i + 1]
                if nxt == "\u094d":  # Halant / virama: suppresses vowel
                    res.append(cons)
                    i += 2
                    continue
                elif nxt in MATRAS:
                    res.append(cons + MATRAS[nxt])
                    i += 2
                    continue
                elif nxt in ("\u0902", "\u0901"):  # Anusvara / candrabindu
                    res.append(cons + "an")
                    i += 2
                    continue
                else:
                    # Inherent vowel 'a'
                    res.append(cons + "a")
                    i += 1
                    continue
            else:
                # Word-final consonant: standard Hindi schwa deletion
                res.append(cons)
                i += 1
                continue

        elif c in VOWELS:
            res.append(VOWELS[c])
            i += 1
        elif c in MATRAS:
            res.append(MATRAS[c])
            i += 1
        elif c in ("\u0902", "\u0901"):
            res.append("n")
            i += 1
        elif c == "\u0903":  # Visarga
            res.append("h")
            i += 1
        elif c in ("\u0964", "\u0965"):  # Danda / double danda
            res.append(".")
            i += 1
        else:
            res.append(c)
            i += 1

    out = "".join(res)

    # Apply Hindi schwa deletion for VC_CV: e.g. "karana" -> "karna", "samajha" -> "samjha"
    out = re.sub(
        r"([aeiou])([kghjtdnpbmyrvlsh])a([kghjtdnpbmyrvlsh])([aeiou])",
        r"\1\2\3\4",
        out,
    )
    return out


def transliterate_token(token: str) -> str:
    """Transliterate a single token, preserving surrounding punctuation and whitespace."""
    if not token:
        return token

    # Fast path if no Devanagari characters
    if not has_devanagari(token):
        if token == "।":
            return "."
        if token == "॥":
            return "."
        return token

    # Check for direct dictionary match
    clean_token = token.strip()
    if clean_token in HINDI_TO_HINGLISH:
        matched = HINDI_TO_HINGLISH[clean_token]
        # Preserve whitespace
        prefix = token[: len(token) - len(token.lstrip())]
        suffix = token[len(token.rstrip()) :]
        return f"{prefix}{matched}{suffix}"

    # Normalize dandas in token
    token = token.replace("\u0964", ".").replace("\u0965", ".")

    # Split leading and trailing punctuation/symbols while keeping Devanagari letters in core
    # Devanagari range is \u0900-\u097F
    lead_m = re.match(r"^([^A-Za-z0-9\u0900-\u097F]*)(.*)$", token, flags=re.DOTALL)
    lead, rest = lead_m.groups() if lead_m else ("", token)

    trail_m = re.search(r"([^A-Za-z0-9\u0900-\u097F]*)$", rest, flags=re.DOTALL)
    if trail_m and trail_m.group(1):
        core = rest[: -len(trail_m.group(1))]
        trail = trail_m.group(1)
    else:
        core = rest
        trail = ""

    if not core:
        return token

    # Check core in dictionary
    if core in HINDI_TO_HINGLISH:
        core_res = HINDI_TO_HINGLISH[core]
    else:
        core_res = _algorithmic_transliterate_word(core)

    return f"{lead}{core_res}{trail}"


def devanagari_to_hinglish(text: Optional[str]) -> str:
    """Convert any Devanagari (Hindi) text into Hinglish (English/Latin spelling).

    Examples:
        'ये क्या हो गया' -> 'ye kya ho gaya'
        'नमस्ते दोस्तों' -> 'namaste dosto'
        'ये क्या hogaya?' -> 'ye kya hogaya?'
        'चैनल को सब्सक्राइब करो।' -> 'channel ko subscribe karo.'
    """
    if not text or not has_devanagari(text):
        return text or ""

    # Replace Hindi full-stop marks (danda) with standard period
    text = text.replace("\u0964", ".").replace("\u0965", ".")

    # Tokenize by whitespace while preserving all spaces
    tokens = re.split(r"(\s+)", text)
    return "".join(transliterate_token(t) for t in tokens)


def transliterate_transcript_words(
    words: Optional[List[Dict[str, Any]]]
) -> List[Dict[str, Any]]:
    """Transliterate word dictionaries in-place for word-level subtitles."""
    if not words:
        return words or []

    for w in words:
        raw_text = w.get("text") or w.get("word") or ""
        if has_devanagari(raw_text):
            converted = devanagari_to_hinglish(raw_text)
            w["text"] = converted
            if "word" in w:
                w["word"] = converted

    return words


def transliterate_transcript_utterances(
    utterances: Optional[List[Dict[str, Any]]]
) -> List[Dict[str, Any]]:
    """Transliterate utterances and their nested words in-place."""
    if not utterances:
        return utterances or []

    for u in utterances:
        if has_devanagari(u.get("text")):
            u["text"] = devanagari_to_hinglish(u.get("text"))
        if u.get("words"):
            transliterate_transcript_words(u["words"])

    return utterances


def transliterate_transcript_payload(
    payload: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Transliterate a full transcript cache payload dictionary."""
    if not payload or not isinstance(payload, dict):
        return payload or {}

    if payload.get("words"):
        transliterate_transcript_words(payload["words"])

    if payload.get("utterances"):
        transliterate_transcript_utterances(payload["utterances"])

    if has_devanagari(payload.get("text")):
        payload["text"] = devanagari_to_hinglish(payload.get("text"))

    return payload
