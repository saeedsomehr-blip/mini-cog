from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, Signal

from app.paths import AppPaths
from services.audio.instruction_player import InstructionPlayer
from services.audio.manifest import InstructionManifest


class InstructionService(QObject):
    """
    Global instruction playback service:
    - Resolves instruction keys via manifest.json
    - Plays audio via QMediaPlayer
    - Drives avatar speaking state (playing => speaking True)
    """

    speakingChanged = Signal(bool)
    started = Signal(str)    # key
    finished = Signal(str)   # key
    error = Signal(str)      # message

    def __init__(self, paths: AppPaths, language: str, parent=None):
        super().__init__(parent)

        self._paths = paths
        self._language = language

        manifest_path = (paths.assets_dir / "audio" / "manifest.json").resolve()
        self._manifest = InstructionManifest.load_from_file(manifest_path)

        self._player = InstructionPlayer(self)

        self._current_key: Optional[str] = None

        self._player.started.connect(self._on_started)
        self._player.finished.connect(self._on_finished)
        self._player.error.connect(self._on_error)

    def set_language(self, language: str) -> None:
        # Update current language for future resolve/play
        self._language = language

    def play(self, key: str) -> None:
        # Resolve key -> path and play
        try:
            audio_path = self._manifest.resolve(self._paths.assets_dir, self._language, key)
            if not audio_path.exists():
                raise FileNotFoundError(str(audio_path))
        except Exception as e:
            self.error.emit(f"Instruction resolve/play failed: {e}")
            return

        self._current_key = key
        self._player.play_file(audio_path)

    def stop(self) -> None:
        self._player.stop()
        self.speakingChanged.emit(False)

    def set_volume(self, volume_0_to_1: float) -> None:
        self._player.set_volume(volume_0_to_1)

    def current_key(self) -> Optional[str]:
        return self._current_key

    def _on_started(self) -> None:
        if self._current_key:
            self.speakingChanged.emit(True)
            self.started.emit(self._current_key)

    def _on_finished(self) -> None:
        self.speakingChanged.emit(False)
        if self._current_key:
            self.finished.emit(self._current_key)

    def _on_error(self, msg: str) -> None:
        self.speakingChanged.emit(False)
        self.error.emit(msg)
