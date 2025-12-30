from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Callable, Sequence
import re

from faster_whisper import WhisperModel
from faster_whisper import utils as whisper_utils
import huggingface_hub

from services.stt.types import TranscriptionResult
from services.stt.device_selector import DeviceChoice, iter_device_choices


class WhisperService:
    def __init__(
        self,
        model_name: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
        download_root: str | Path | None = None,
        local_files_only: bool = False,
        fallback: list[DeviceChoice] | None = None,
    ):
        self._model_name = model_name
        self._device = device
        self._compute_type = compute_type
        self._download_root = str(Path(download_root).resolve()) if download_root is not None else None
        self._local_files_only = bool(local_files_only)
        self._fallback = list(fallback) if fallback is not None else []

        self._model: WhisperModel | None = None

    def _ensure_model(self) -> WhisperModel:
        if self._model is None:
            choices = [DeviceChoice(self._device, self._compute_type)] + list(self._fallback)
            last_exc: Exception | None = None
            for choice in choices:
                try:
                    self._model = WhisperModel(
                        self._model_name,
                        device=choice.device,
                        compute_type=choice.compute_type,
                        download_root=self._download_root,
                        local_files_only=self._local_files_only,
                    )
                    if choice.device != self._device or choice.compute_type != self._compute_type:
                        self._device = choice.device
                        self._compute_type = choice.compute_type
                    break
                except (RuntimeError, ValueError) as exc:
                    last_exc = exc
                    continue
            if self._model is None:
                if self._local_files_only and isinstance(last_exc, RuntimeError):
                    raise RuntimeError(
                        "Offline mode is enabled but the Whisper model files are missing. "
                        "Download the model once (disable offline mode) and retry."
                    ) from last_exc
                if last_exc is not None:
                    raise last_exc
        return self._model

    def preload(self) -> None:
        self._ensure_model()

    def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = "en",
        *,
        beam_size: Optional[int] = None,
        vad_filter: Optional[bool] = None,
        without_timestamps: Optional[bool] = None,
        grammar: Optional[Sequence[str]] = None,
    ) -> TranscriptionResult:
        _ = grammar
        model = self._ensure_model()
        transcribe_kwargs = {"language": language}
        if beam_size is not None:
            transcribe_kwargs["beam_size"] = beam_size
        if vad_filter is not None:
            transcribe_kwargs["vad_filter"] = vad_filter
        if without_timestamps is not None:
            transcribe_kwargs["without_timestamps"] = without_timestamps
        segments, info = model.transcribe(str(audio_path), **transcribe_kwargs)
        text = " ".join(seg.text.strip() for seg in segments if seg.text)
        return TranscriptionResult(text=text, language=getattr(info, "language", None))


def resolve_model_name(language: str) -> str:
    return "large-v3" if language.lower().startswith("fa") else "small"


def download_whisper_model(
    model_name: str,
    download_root: str | Path | None,
    *,
    progress_cb: Optional[Callable[[int], None]] = None,
) -> str:
    if re.match(r".*/.*", model_name):
        repo_id = model_name
    else:
        repo_id = whisper_utils._MODELS.get(model_name)
        if repo_id is None:
            raise ValueError(
                "Invalid model size '%s', expected one of: %s"
                % (model_name, ", ".join(whisper_utils._MODELS.keys()))
            )

    allow_patterns = [
        "config.json",
        "preprocessor_config.json",
        "model.bin",
        "tokenizer.json",
        "vocabulary.*",
    ]

    class UiProgress:
        def __init__(self, total=None, **kwargs):
            self.total = total or 0
            self.n = 0
            self._last = -1
            if progress_cb is not None and self.total:
                progress_cb(0)

        def update(self, n):
            self.n += n
            if self.total and progress_cb is not None:
                percent = int((self.n / self.total) * 100)
                if percent != self._last:
                    self._last = percent
                    progress_cb(percent)

        def close(self):
            if progress_cb is not None and self.total:
                progress_cb(100)

    kwargs = {
        "local_files_only": False,
        "allow_patterns": allow_patterns,
        "tqdm_class": UiProgress,
    }
    if download_root is not None:
        kwargs["cache_dir"] = str(Path(download_root).resolve())
    return huggingface_hub.snapshot_download(repo_id, **kwargs)


def build_whisper_service(
    language: str,
    download_root: str | Path | None,
    local_files_only: bool = True,
    device: str = "cpu",
    compute_type: str = "int8",
) -> WhisperService:
    if os.environ.get("MINICOG_STT_ALLOW_DOWNLOAD") == "1":
        local_files_only = False
    preferred = [
        DeviceChoice(device=device, compute_type=compute_type),
        DeviceChoice(device="cpu", compute_type="int8"),
    ]
    choices = iter_device_choices(preferred)
    model_name = resolve_model_name(language)
    return WhisperService(
        model_name=model_name,
        device=choices[0].device,
        compute_type=choices[0].compute_type,
        download_root=download_root,
        local_files_only=local_files_only,
        fallback=choices[1:],
    )
