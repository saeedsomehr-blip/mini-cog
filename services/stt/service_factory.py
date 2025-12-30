from __future__ import annotations

from pathlib import Path

from services.stt.base import STTService
from services.stt.vosk_service import VoskService
from services.stt.whisper_service import build_whisper_service

VOSK_MODEL_DIRS = {
    "fa": "vosk-model-small-fa-0.4",
    "en": "vosk-model-small-en-us-0.15",
}


def get_vosk_model_path(language: str, cache_root: str | Path) -> Path | None:
    lang = language.lower()
    if lang.startswith("fa"):
        key = "fa"
    elif lang.startswith("en"):
        key = "en"
    else:
        return None
    return Path(cache_root) / "vosk" / VOSK_MODEL_DIRS[key]


def build_stt_service(
    language: str,
    cache_root: str | Path,
    local_files_only: bool = True,
    device: str = "cpu",
    compute_type: str = "int8",
) -> STTService:
    vosk_path = get_vosk_model_path(language, cache_root)
    if vosk_path is not None:
        return VoskService(model_path=vosk_path)
    whisper_root = Path(cache_root) / "whisper"
    return build_whisper_service(
        language=language,
        download_root=whisper_root,
        local_files_only=local_files_only,
        device=device,
        compute_type=compute_type,
    )
