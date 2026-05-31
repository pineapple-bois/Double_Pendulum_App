from dataclasses import dataclass
from enum import StrEnum


class SimulationResultState(StrEnum):
    SUCCESS = "success"
    VALIDATION_ERROR = "validation_error"
    SOLVER_FAILURE = "solver_failure"
    EMPTY_OR_CLEARED = "empty_or_cleared"


@dataclass(frozen=True)
class SimulationResultContract:
    state: SimulationResultState
    render_safe: bool
    user_message: str
    debug_message: str | None = None


def success_result(user_message: str, debug_message: str | None = None) -> SimulationResultContract:
    return SimulationResultContract(
        state=SimulationResultState.SUCCESS,
        render_safe=True,
        user_message=user_message,
        debug_message=debug_message,
    )


def validation_error_result(user_message: str, debug_message: str | None = None) -> SimulationResultContract:
    return SimulationResultContract(
        state=SimulationResultState.VALIDATION_ERROR,
        render_safe=False,
        user_message=user_message,
        debug_message=debug_message,
    )


def solver_failure_result(user_message: str, debug_message: str | None = None) -> SimulationResultContract:
    return SimulationResultContract(
        state=SimulationResultState.SOLVER_FAILURE,
        render_safe=False,
        user_message=user_message,
        debug_message=debug_message,
    )


def empty_or_cleared_result(user_message: str, debug_message: str | None = None) -> SimulationResultContract:
    return SimulationResultContract(
        state=SimulationResultState.EMPTY_OR_CLEARED,
        render_safe=False,
        user_message=user_message,
        debug_message=debug_message,
    )
