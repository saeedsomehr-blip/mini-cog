from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from domain.models import Session, StepResult
from domain.protocol import StepID, first_step, next_step


logger = logging.getLogger(__name__)


@dataclass
class FlowState:
    # Keeps track of current session and step
    session: Session
    current_step: StepID


class AppController:
    """
    Central app controller:
    - Creates sessions
    - Tracks current step
    - Accepts step results
    - Determines next navigation target
    """

    def __init__(self):
        self._state: Optional[FlowState] = None

    def start_new_session(self, language: str = "fa") -> FlowState:
        # Create a new session and set initial step
        session = Session(language=language)
        state = FlowState(session=session, current_step=first_step())
        self._state = state
        logger.info("New session started: %s", session.session_id)
        return state

    def get_state(self) -> Optional[FlowState]:
        # Return current flow state
        return self._state

    def submit_step_result(self, result: StepResult) -> StepID:
        # Persist the result into the current session and advance step
        if self._state is None:
            raise RuntimeError("No active session. Call start_new_session() first.")

        result.mark_finished()
        self._state.session.set_result(result)

        # Advance to next step
        self._state.current_step = next_step(result.step_id)
        logger.info("Step completed: %s -> next: %s", result.step_id.value, self._state.current_step.value)
        return self._state.current_step

    def step_to_route(self, step_id: StepID) -> str:
        # Map a step ID to a router route name
        return step_id.value
