from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class DeviceChoice:
    device: str
    compute_type: str


def iter_device_choices(preferred: Iterable[DeviceChoice]) -> list[DeviceChoice]:
    """
    Return the ordered list of device choices; actual viability is checked by model init.
    """
    return list(preferred)
