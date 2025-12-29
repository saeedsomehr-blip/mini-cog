from __future__ import annotations

import random
from typing import List, Tuple

WORD_LISTS = {
    "en": {
        "Version 1": ["Banana", "Sunrise", "Chair"],
        "Version 2": ["Leader", "Season", "Table"],
        "Version 3": ["Village", "Kitchen", "Baby"],
        "Version 4": ["River", "Nation", "Finger"],
        "Version 5": ["Captain", "Garden", "Picture"],
        "Version 6": ["Daughter", "Heaven", "Mountain"],
    },
    "fa": {
        "نسخه ۱": ["موز", "طلوع", "صندلی"],
        "نسخه ۲": ["رهبر", "فصل", "میز"],
        "نسخه ۳": ["روستا", "آشپزخانه", "کودک"],
        "نسخه ۴": ["رود", "دولت", "انگشت"],
        "نسخه ۵": ["فرمانده", "باغ", "تصویر"],
        "نسخه ۶": ["دختر", "بهشت", "کوه"],
    },
}


def select_word_list(language: str = "en") -> Tuple[str, List[str]]:
    lang = language if language in WORD_LISTS else "en"
    versions = list(WORD_LISTS[lang].keys())
    version = random.choice(versions)
    return version, WORD_LISTS[lang][version]
