from __future__ import annotations

import json
import wave
from pathlib import Path
from typing import Optional, Sequence

try:
    from vosk import KaldiRecognizer, Model, SetLogLevel
except Exception:  # pragma: no cover - optional dependency
    KaldiRecognizer = None
    Model = None
    SetLogLevel = None

from services.stt.types import TranscriptionResult


class VoskService:
    def __init__(self, model_path: str | Path):
        self._model_path = Path(model_path)
        self._model: Model | None = None
        if SetLogLevel is not None:
            SetLogLevel(-1)

    def _ensure_model(self) -> Model:
        if Model is None or KaldiRecognizer is None:
            raise RuntimeError("Vosk is not installed. Install the 'vosk' package to enable Persian STT.")
        if self._model is None:
            if not self._model_path.exists():
                raise RuntimeError(
                    f"Vosk model not found at {self._model_path}. "
                    "Download the Persian model and extract it into this folder."
                )
            self._model = Model(str(self._model_path))
        return self._model

    def preload(self) -> None:
        self._ensure_model()

    def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = "fa",
        *,
        grammar: Optional[Sequence[str]] = None,
        **kwargs,
    ) -> TranscriptionResult:
        _ = kwargs
        model = self._ensure_model()
        with wave.open(str(audio_path), "rb") as wav_file:
            sample_rate = wav_file.getframerate()
            if grammar:
                recognizer = KaldiRecognizer(
                    model,
                    sample_rate,
                    json.dumps(list(grammar), ensure_ascii=False),
                )
            else:
                recognizer = KaldiRecognizer(model, sample_rate)
            recognizer.SetWords(True)
            while True:
                data = wav_file.readframes(4000)
                if len(data) == 0:
                    break
                recognizer.AcceptWaveform(data)
            result = json.loads(recognizer.FinalResult())
            text = (result.get("text") or "").strip()
        word_confidences = []
        for item in result.get("result", []) or []:
            if "word" in item and "conf" in item:
                word_confidences.append({"word": item["word"], "conf": item["conf"]})
        confidence = None
        if word_confidences:
            confidence = sum(item["conf"] for item in word_confidences) / len(word_confidences)
        return TranscriptionResult(
            text=text,
            language=language,
            confidence=confidence,
            word_confidences=word_confidences or None,
        )
