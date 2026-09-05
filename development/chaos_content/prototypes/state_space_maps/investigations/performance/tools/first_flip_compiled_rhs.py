"""Investigation-only compiled physical RHS for the first-flip reference.

Only the four-state Euler--Lagrange RHS is compiled. The operational
``first_flip_time`` function continues to own solve_ivp, its four terminal
events, root finding, diagnostics, statuses, and censoring semantics.
"""

from __future__ import annotations

import math
from typing import Callable

import numpy as np
from numba import njit

from ....src.first_flip.reference import FirstFlipResult, first_flip_time
from ....src.lyapunov.reference import (
    EulerLagrangeState,
    PendulumParameters,
    SolverSpec,
)


PROTOTYPE_IDENTITY = "investigation_first_flip_numba_4state_rhs_v1"


@njit(cache=True)
def compiled_physical_rhs(
    time_value: float,
    state: np.ndarray,
    length1: float,
    length2: float,
    mass1: float,
    mass2: float,
    gravity: float,
) -> np.ndarray:
    """Return the unchanged four-state absolute-angle physical flow."""

    theta1, theta2, omega1, omega2 = state
    angle_difference = theta1 - theta2
    sine_difference = math.sin(angle_difference)
    cosine_difference = math.cos(angle_difference)
    denominator = 2.0 * mass1 + mass2 - mass2 * math.cos(
        2.0 * angle_difference
    )

    first_inner = (
        length2 * omega2 * omega2
        + length1 * omega1 * omega1 * cosine_difference
    )
    first_acceleration = (
        -gravity * (2.0 * mass1 + mass2) * math.sin(theta1)
        - mass2 * gravity * math.sin(theta1 - 2.0 * theta2)
        - 2.0 * mass2 * sine_difference * first_inner
    ) / (length1 * denominator)

    second_inner = (
        length1 * omega1 * omega1 * (mass1 + mass2)
        + gravity * (mass1 + mass2) * math.cos(theta1)
        + length2 * mass2 * omega2 * omega2 * cosine_difference
    )
    second_acceleration = (
        2.0 * sine_difference * second_inner
    ) / (length2 * denominator)

    result = np.empty(4, dtype=np.float64)
    result[0] = omega1
    result[1] = omega2
    result[2] = first_acceleration
    result[3] = second_acceleration
    return result


def compiled_rhs(
    parameters: PendulumParameters,
) -> Callable[[float, np.ndarray], np.ndarray]:
    """Bind physical parameters around the investigation kernel."""

    values = (
        parameters.length1,
        parameters.length2,
        parameters.mass1,
        parameters.mass2,
        parameters.gravity,
    )

    def evaluate(time_value: float, state: np.ndarray) -> np.ndarray:
        return compiled_physical_rhs(time_value, state, *values)

    return evaluate


def warm_compiled_rhs(parameters: PendulumParameters) -> None:
    """Exclude one-time Numba compilation from warm repeated cell timings."""

    compiled_rhs(parameters)(0.0, np.zeros(4, dtype=np.float64))


def first_flip_time_compiled_rhs(
    initial_state: EulerLagrangeState | tuple[float, float, float, float],
    parameters: PendulumParameters | None = None,
    solver_spec: SolverSpec | None = None,
    observation_horizon: float = 5.0,
) -> FirstFlipResult:
    """Run the exact operational event contract with only its RHS replaced."""

    fixed_parameters = parameters or PendulumParameters()
    return first_flip_time(
        initial_state,
        parameters=fixed_parameters,
        solver_spec=solver_spec,
        observation_horizon=observation_horizon,
        _rhs_override=compiled_rhs(fixed_parameters),
    )
