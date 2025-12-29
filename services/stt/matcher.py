from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class MatchResult:
    matched: List[str]
    missed: List[str]
    score: int
    transcript: str


def _normalize(text: str) -> List[str]:
    # Normalize Persian/Arabic variants and remove diacritics.
    text = text.lower()
    text = text.replace("\u200c", " ")
    text = text.replace("\u060c", " ")
    text = text.replace("ي", "ی").replace("ك", "ک")
    text = re.sub(r"[\u064b-\u065f\u0670\u06d6-\u06ed]", "", text)
    clean = re.sub(r"[^\w\s\u0600-\u06ff]", " ", text)
    return [w for w in clean.split() if w]


def match_words(transcript: str, target_words: List[str]) -> MatchResult:
    normalized = set(_normalize(transcript))
    matched = []
    missed = []
    for word in target_words:
        if word.lower() in normalized:
            matched.append(word)
        else:
            missed.append(word)
    return MatchResult(matched=matched, missed=missed, score=len(matched), transcript=transcript)
