from __future__ import annotations

from typing import Optional


def decision_from_confidence(confidence: Optional[float], threshold: float = 0.6) -> str:
    if confidence is None:
        return "uncertain"
    return "accepted" if confidence >= threshold else "uncertain"
