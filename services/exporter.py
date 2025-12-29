from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Dict

from domain.models import Session


def export_session(session: Session, export_dir: Path) -> Dict[str, str]:
    export_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"session_{session.session_id}_{timestamp}"

    json_path = export_dir / f"{base}.json"
    csv_path = export_dir / f"{base}_summary.csv"

    json_path.write_text(_to_json(session), encoding="utf-8")
    _write_csv_summary(session, csv_path)

    return {"json": str(json_path), "csv": str(csv_path)}


def _to_json(session: Session) -> str:
    import json

    return json.dumps(session.to_dict(), ensure_ascii=False, indent=2)


def _write_csv_summary(session: Session, path: Path) -> None:
    summary = _build_summary_row(session)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerow(summary)


def _build_summary_row(session: Session) -> Dict[str, str]:
    reg = session.results.get("registration")
    clock = session.results.get("clock")
    recall = session.results.get("recall")

    reg_attempts = ""
    words_presented = ""
    if reg and reg.payload:
        reg_attempts = str(len(reg.payload.get("attempts") or []))
        words_presented = " | ".join(reg.payload.get("words_presented") or [])

    clock_numbers = ""
    clock_hands_complete = ""
    clock_ended = ""
    if clock and clock.payload:
        numbers = clock.payload.get("numbers") or {}
        hands = clock.payload.get("hands") or {}
        clock_numbers = str(numbers.get("count", ""))
        clock_hands_complete = str(bool(hands.get("complete", False)))
        clock_ended = str(clock.payload.get("ended_reason") or "")

    recall_score = ""
    recall_matched = ""
    recall_missed = ""
    if recall and recall.payload:
        recall_score = str(recall.payload.get("score", ""))
        recall_matched = " | ".join(recall.payload.get("matched") or [])
        recall_missed = " | ".join(recall.payload.get("missed") or [])

    return {
        "session_id": session.session_id,
        "language": session.language or "",
        "patient_name": session.patient_name or "",
        "patient_age": str(session.patient_age) if session.patient_age is not None else "",
        "registration_time": session.registration_time or "",
        "word_list_version": session.word_list_version or "",
        "words_presented": words_presented,
        "registration_attempts": reg_attempts,
        "clock_numbers_count": clock_numbers,
        "clock_hands_complete": clock_hands_complete,
        "clock_ended_reason": clock_ended,
        "recall_score": recall_score,
        "recall_matched": recall_matched,
        "recall_missed": recall_missed,
    }
