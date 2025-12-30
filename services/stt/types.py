from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    language: Optional[str] = None
    confidence: Optional[float] = None
    word_confidences: Optional[list[dict]] = None
