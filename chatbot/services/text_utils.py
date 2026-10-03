"""
Cheap, rule-based text cleanup that runs BEFORE embeddings/alias matching.
Keeps Urdu script and Roman Urdu intact; only strips noise and fixes a
handful of very common spelling variants so alias/substring matching
doesn't miss obvious near-duplicates.

This is intentionally small. Extend SPELLING_VARIANTS as you see real
queries come in during testing — don't try to guess every variant up
front.
"""
import re
import unicodedata

SPELLING_VARIANTS = {
    "kiya": "kya", "kya h": "kya hai", "kha": "kahan", "kahn": "kahan",
    "kb": "kab", "kon": "kaun", "kn": "kaun", "fee": "fees",
    "no": "number", "num": "number", "plz": "please", "pls": "please",
    "university": "university", "varsity": "university",
}

_PUNCT_RE = re.compile(r"[^\w\s#]", re.UNICODE)
_SPACE_RE = re.compile(r"\s+")


def normalize(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = text.strip().lower()
    text = _PUNCT_RE.sub(" ", text)
    text = _SPACE_RE.sub(" ", text).strip()

    words = text.split(" ")
    words = [SPELLING_VARIANTS.get(w, w) for w in words]
    return " ".join(words)
