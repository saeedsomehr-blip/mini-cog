from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from domain.protocol import StepID


def utc_now_iso() -> str:
    # Return current UTC time as ISO-8601 string
    return datetime.now(timezone.utc).isoformat()


def local_now_iso() -> str:
    # Return local time as ISO-8601 string
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class StepResult:
    # Generic container for a step's recorded data and scores
    step_id: StepID
    started_at: str = field(default_factory=utc_now_iso)
    finished_at: Optional[str] = None

    # Step-specific payload:
    # - registration: { "word_list_id": "...", "words": [...], "attempts": [...], ... }
    # - clock:        { "image_path": "...", "clock_score": 0|2, ... }
    # - recall:       { "audio_path": "...", "transcript": "...", "recall_score": 0..3, ... }
    payload: Dict[str, Any] = field(default_factory=dict)

    # Convenience numeric score (optional; total computed elsewhere)
    score: Optional[int] = None

    def mark_finished(self) -> None:
        # Mark the step as finished
        self.finished_at = utc_now_iso()


@dataclass
class Session:
    # Represents one Mini-Cog administration session
    session_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utc_now_iso)
    language: str = "fa"

    # Patient/admin data captured at registration
    patient_name: str = ""
    patient_age: Optional[int] = None
    registration_time: Optional[str] = None
    word_list_version: Optional[str] = None
    words_presented: list[str] = field(default_factory=list)

    # Chosen word list for this session (set during registration)
    word_list_id: Optional[str] = None
    words: list[str] = field(default_factory=list)

    # Collected results by step
    results: Dict[str, StepResult] = field(default_factory=dict)

    def set_result(self, result: StepResult) -> None:
        # Store a step result using the step_id value as key (stable for JSON)
        self.results[result.step_id.value] = result

    def get_result(self, step_id: StepID) -> Optional[StepResult]:
        # Retrieve a step result if available
        return self.results.get(step_id.value)

    def to_dict(self) -> Dict[str, Any]:
        # Serialize to a JSON-friendly dict
        return asdict(self)
