from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput


class InstructionPlayer(QObject):
    # Signals for UI updates
    started = Signal()
    finished = Signal()
    error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._audio_out = QAudioOutput(self)
        self._player = QMediaPlayer(self)
        self._player.setAudioOutput(self._audio_out)

        self._player.playbackStateChanged.connect(self._on_state_changed)
        self._player.errorOccurred.connect(self._on_error)

    def media_player(self) -> QMediaPlayer:
        # Expose the underlying player for optional probing
        return self._player

    def play_file(self, path: str | Path) -> None:
        # Play a local audio file
        p = Path(path).resolve()
        self._player.setSource(QUrl.fromLocalFile(str(p)))
        self._player.play()

    def stop(self) -> None:
        self._player.stop()

    def set_volume(self, volume_0_to_1: float) -> None:
        # QAudioOutput volume is [0..1]
        v = max(0.0, min(1.0, float(volume_0_to_1)))
        self._audio_out.setVolume(v)

    def _on_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        if state == QMediaPlayer.PlayingState:
            self.started.emit()
        elif state == QMediaPlayer.StoppedState:
            self.finished.emit()

    def _on_error(self, _err, err_str: str) -> None:
        if err_str:
            self.error.emit(err_str)
