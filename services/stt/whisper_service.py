from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Optional

from faster_whisper import WhisperModel


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    language: Optional[str] = None


class WhisperService:
    def __init__(
        self,
        model_name: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
        download_root: str | Path | None = None,
        local_files_only: bool = False,
    ):
        self._model_name = model_name
        self._device = device
        self._compute_type = compute_type
        self._download_root = str(Path(download_root).resolve()) if download_root is not None else None
        self._local_files_only = bool(local_files_only)

        self._model: WhisperModel | None = None

    def _ensure_model(self) -> WhisperModel:
        if self._model is None:
            try:
                self._model = WhisperModel(
                    self._model_name,
                    device=self._device,
                    compute_type=self._compute_type,
                    download_root=self._download_root,
                    local_files_only=self._local_files_only,
                )
            except RuntimeError as exc:
                if self._local_files_only:
                    raise RuntimeError(
                        "Offline mode is enabled but the Whisper model files are missing. "
                        "Download the model once (disable offline mode) and retry."
                    ) from exc
                raise
        return self._model

    def preload(self) -> None:
        self._ensure_model()

    def transcribe(self, audio_path: Path, language: Optional[str] = "en") -> TranscriptionResult:
        model = self._ensure_model()
        segments, info = model.transcribe(str(audio_path), language=language)
        text = " ".join(seg.text.strip() for seg in segments if seg.text)
        return TranscriptionResult(text=text, language=getattr(info, "language", None))


def build_whisper_service(
    language: str,
    download_root: str | Path | None,
    local_files_only: bool = True,
    device: str = "cpu",
    compute_type: str = "int8",
) -> WhisperService:
    if os.environ.get("MINICOG_STT_ALLOW_DOWNLOAD") == "1":
        local_files_only = False
    model_name = "small"
    return WhisperService(
        model_name=model_name,
        device=device,
        compute_type=compute_type,
        download_root=download_root,
        local_files_only=local_files_only,
    )
