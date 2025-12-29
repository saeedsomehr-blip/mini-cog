from __future__ import annotations

import math
import struct
from typing import Optional

from PySide6.QtCore import QObject, Signal, QTimer

# Probe is not guaranteed to exist in every build/backend
try:
    from PySide6.QtMultimedia import QAudioProbe, QAudioBuffer, QAudioFormat
    _HAS_PROBE = True
except Exception:
    QAudioProbe = None  # type: ignore
    QAudioBuffer = None  # type: ignore
    QAudioFormat = None  # type: ignore
    _HAS_PROBE = False


class MouthAnimator(QObject):
    """
    Emits speaking(bool) based on audio energy.
    - If QAudioProbe is available, computes RMS from audio buffers.
    - Otherwise, falls back to a simple timer-based "talking" effect.
    """

    speakingChanged = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._speaking = False

        self._probe: Optional[object] = None
        self._fallback_timer = QTimer(self)
        self._fallback_timer.setInterval(120)  # ms
        self._fallback_timer.timeout.connect(self._fallback_tick)

        # Tunable thresholds
        self._open_threshold = 0.08  # RMS normalized threshold

        if _HAS_PROBE:
            self._probe = QAudioProbe(self)

    def attach_to_player(self, media_player) -> None:
        """
        Attach to a QMediaPlayer instance.
        """
        if _HAS_PROBE and self._probe is not None:
            # If probe attach fails (backend), we can still fallback
            ok = self._probe.setSource(media_player)  # type: ignore[attr-defined]
            if ok:
                self._probe.audioBufferProbed.connect(self._on_buffer)  # type: ignore[attr-defined]
                return

        # Probe not available or failed
        self._probe = None

    def start_fallback(self) -> None:
        self._fallback_timer.start()

    def stop_all(self) -> None:
        self._fallback_timer.stop()
        self._set_speaking(False)

    def _fallback_tick(self) -> None:
        # Simple alternating mouth open/close
        self._set_speaking(not self._speaking)

    def _set_speaking(self, s: bool) -> None:
        if self._speaking == s:
            return
        self._speaking = s
        self.speakingChanged.emit(s)

    def _on_buffer(self, buf) -> None:
        """
        Compute RMS energy from audio buffer and decide speaking state.
        """
        try:
            fmt = buf.format()
            data = bytes(buf.data())
            if not data:
                self._set_speaking(False)
                return

            # Handle common formats; many backends provide Int16
            sample_format = fmt.sampleFormat()

            if sample_format == QAudioFormat.Int16:
                # Little-endian signed 16-bit
                count = len(data) // 2
                if count <= 0:
                    self._set_speaking(False)
                    return
                samples = struct.unpack("<" + "h" * count, data)
                rms = math.sqrt(sum((s / 32768.0) ** 2 for s in samples) / count)

            elif sample_format == QAudioFormat.UInt8:
                # 8-bit unsigned centered at 128
                count = len(data)
                samples = data
                rms = math.sqrt(sum((((b - 128) / 128.0) ** 2) for b in samples) / count)

            else:
                # Unknown format -> do not overcomplicate; fallback behavior
                self._set_speaking(True)
                return

            self._set_speaking(rms >= self._open_threshold)

        except Exception:
            # On any parsing issue, be conservative
            self._set_speaking(True)
