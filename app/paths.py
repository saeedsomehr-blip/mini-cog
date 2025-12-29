from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


def _get_bundle_root() -> Path:
    """
    When packaged (e.g., PyInstaller), resources may live in a temporary folder.
    This function returns the base directory to resolve assets reliably.
    """
    if hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS")).resolve()  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class AppPaths:
    app_name: str
    project_root: Path
    assets_dir: Path
    data_dir: Path
    cache_dir: Path
    logs_dir: Path
    exports_dir: Path

    @staticmethod
    def from_default_locations(app_name: str) -> "AppPaths":
        # Resolve bundled/project root for reading packaged assets
        root = _get_bundle_root()

        # Store user-writable data under home directory
        base = Path.home() / f".{app_name}"
        data_dir = base / "data"
        cache_dir = base / "cache"
        logs_dir = base / "logs"
        exports_dir = base / "exports"

        assets_dir = root / "assets"
        return AppPaths(
            app_name=app_name,
            project_root=root,
            assets_dir=assets_dir,
            data_dir=data_dir,
            cache_dir=cache_dir,
            logs_dir=logs_dir,
            exports_dir=exports_dir,
        )

    def ensure_dirs(self) -> None:
        # Ensure user-writable folders exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
