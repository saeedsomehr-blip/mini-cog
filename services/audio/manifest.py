from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


@dataclass(frozen=True)
class InstructionManifest:
    # Holds mapping: language -> { key -> relative_path }
    mapping: Dict[str, Dict[str, str]]

    @staticmethod
    def load_from_file(path: Path) -> "InstructionManifest":
        # Load JSON manifest that maps instruction keys to audio paths
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Invalid manifest format: top-level must be an object.")
        # Ensure nested dict structure
        mapping: Dict[str, Dict[str, str]] = {}
        for lang, d in data.items():
            if isinstance(lang, str) and isinstance(d, dict):
                mapping[lang] = {str(k): str(v) for k, v in d.items()}
        return InstructionManifest(mapping=mapping)

    def resolve(self, assets_dir: Path, language: str, key: str) -> Path:
        # Resolve an instruction key to an absolute file path under assets_dir
        lang_map = self.mapping.get(language) or {}
        rel = lang_map.get(key)
        if not rel:
            raise KeyError(f"Instruction key not found in manifest for language '{language}': {key}")
        return (assets_dir / rel).resolve()
