from __future__ import annotations

import time
import wave
from pathlib import Path


def wait_for_wav_ready(
    path: Path,
    *,
    timeout_s: float = 2.0,
    interval_s: float = 0.2,
    stable_checks: int = 3,
) -> bool:
    """
    Wait until the wav file size is stable and header is readable.
    Returns True if ready, False if timeout.
    """
    deadline = time.time() + timeout_s
    last_size = None
    stable = 0

    while time.time() < deadline:
        if not path.exists():
            time.sleep(interval_s)
            continue

        size = path.stat().st_size
        if last_size is not None and size == last_size:
            stable += 1
        else:
            stable = 0
            last_size = size

        if stable >= stable_checks:
            try:
                with wave.open(str(path), "rb") as wf:
                    wf.getnchannels()
                    wf.getframerate()
                    wf.getsampwidth()
                    wf.getnframes()
                return True
            except Exception:
                stable = 0

        time.sleep(interval_s)

    return False
