from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QAudioInput, QMediaCaptureSession, QMediaFormat, QMediaRecorder


class AudioRecorder(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._audio_input = QAudioInput(self)
        self._capture = QMediaCaptureSession(self)
        self._capture.setAudioInput(self._audio_input)

        self._recorder = QMediaRecorder(self)
        self._capture.setRecorder(self._recorder)

        fmt = QMediaFormat()
        fmt.setFileFormat(QMediaFormat.Wave)
        if hasattr(QMediaFormat.AudioCodec, "PCM"):
            fmt.setAudioCodec(QMediaFormat.AudioCodec.PCM)
        elif hasattr(QMediaFormat.AudioCodec, "LinearPcm"):
            fmt.setAudioCodec(QMediaFormat.AudioCodec.LinearPcm)
        self._recorder.setMediaFormat(fmt)
        if hasattr(self._recorder, "setAudioSampleRate"):
            self._recorder.setAudioSampleRate(16000)
        if hasattr(self._recorder, "setAudioChannelCount"):
            self._recorder.setAudioChannelCount(1)
        if hasattr(self._recorder, "setAudioBitRate"):
            self._recorder.setAudioBitRate(16000 * 16)

        self._output_path: Path | None = None

    def start(self, output_path: Path) -> None:
        self._output_path = output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._recorder.setOutputLocation(QUrl.fromLocalFile(str(output_path)))
        self._recorder.record()

    def stop(self) -> Path | None:
        self._recorder.stop()
        return self._output_path

    def is_recording(self) -> bool:
        return self._recorder.isRecording()
