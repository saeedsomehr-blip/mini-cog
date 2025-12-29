from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class ClockHandsEvalConfig:
    minute_tolerance_deg: float
    hour_tolerance_deg: float


@dataclass
class ClockHandsEvalResult:
    pass_layout: bool
    minute_ok: bool
    hour_ok: bool


def _angle_diff(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def _expected_hand_angles(time_hour: int, time_minute: int) -> Tuple[float, float]:
    # 12 o'clock is 90 degrees, clockwise is decreasing by 30 degrees per hour.
    minute_angle = (90 - (time_minute * 6)) % 360
    hour_value = (time_hour % 12) + (time_minute / 60.0)
    hour_angle = (90 - (hour_value * 30)) % 360
    return minute_angle, hour_angle


def evaluate_clock_hands(
    minute_angle: Optional[float],
    hour_angle: Optional[float],
    config: ClockHandsEvalConfig,
    time_hour: int = 11,
    time_minute: int = 10,
) -> ClockHandsEvalResult:
    if minute_angle is None or hour_angle is None:
        return ClockHandsEvalResult(pass_layout=False, minute_ok=False, hour_ok=False)

    expected_minute, expected_hour = _expected_hand_angles(time_hour, time_minute)

    minute_ok = _angle_diff(minute_angle, expected_minute) <= config.minute_tolerance_deg
    hour_ok = _angle_diff(hour_angle, expected_hour) <= config.hour_tolerance_deg

    return ClockHandsEvalResult(
        pass_layout=minute_ok and hour_ok,
        minute_ok=minute_ok,
        hour_ok=hour_ok,
    )
