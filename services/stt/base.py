from __future__ import annotations

from pathlib import Path
from typing import Optional, Protocol, Sequence

from services.stt.types import TranscriptionResult


class STTService(Protocol):
    def preload(self) -> None:
        ...

    def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = "en",
        *,
        grammar: Optional[Sequence[str]] = None,
        **kwargs,
    ) -> TranscriptionResult:
        ...
