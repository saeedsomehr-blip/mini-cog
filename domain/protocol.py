from __future__ import annotations

from enum import Enum


class StepID(str, Enum):
    # Step identifiers for routing and persistence
    REGISTRATION = "registration"
    CLOCK = "clock"
    RECALL = "recall"
    RESULTS = "results"


def ordered_steps() -> list[StepID]:
    # The canonical Mini-Cog step order for the app flow
    return [
        StepID.REGISTRATION,
        StepID.CLOCK,
        StepID.RECALL,
        StepID.RESULTS,
    ]


def next_step(current: StepID) -> StepID:
    # Get the next step in the canonical flow
    steps = ordered_steps()
    idx = steps.index(current)
    if idx >= len(steps) - 1:
        return StepID.RESULTS
    return steps[idx + 1]


def first_step() -> StepID:
    # Get the first step of the flow
    return StepID.REGISTRATION
