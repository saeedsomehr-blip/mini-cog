from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class I18N:
    # Minimal placeholder for translations; replace with Qt .qm later
    language: str = "fa"

    def t(self, key: str) -> str:
        # Simple key-based translation stub
        return key
