"""Numba RHS equivalent for the fixed-horizon tangent observable.

The compiled path deliberately retains the reference SciPy DOP853 driver,
Candidate-A geometry, renormalisation loop, diagnostics, and result types. Only
the explicit Euler--Lagrange flow and its Jacobian-vector product are
re-expressed as one low-level eight-component Numba kernel.
"""

from __future__ import annotations

import math
from typing import Callable

import numpy as np
from numba import njit

if __package__:
    from .evaluation import (
        RenormalizedTangentEvaluation,
        evaluate_renormalized_tangent_runner,
    )
    from .reference import (
        PendulumParameters,
        RenormalizedTangentResult,
        RenormalizedTangentSpec,
        _run_renormalized_tangent_with_rhs,
    )
else:
    from evaluation import (
        RenormalizedTangentEvaluation,
        evaluate_renormalized_tangent_runner,
    )
    from reference import (
        PendulumParameters,
        RenormalizedTangentResult,
        RenormalizedTangentSpec,
        _run_renormalized_tangent_with_rhs,
    )


COMPILED_EVALUATOR = "numba_rhs_scipy_dop853"


@njit(cache=False)
def compiled_reference_and_tangent_rhs(
    time_value: float,
    augmented: np.ndarray,
    length1: float,
    length2: float,
    mass1: float,
    mass2: float,
    gravity: float,
) -> np.ndarray:
    """Return the EL flow and exact directional derivative ``J(x) delta x``."""

    theta1, theta2, omega1, omega2 = augmented[:4]
    tangent1, tangent2, tangent3, tangent4 = augmented[4:]

    angle_difference = theta1 - theta2
    tangent_angle_difference = tangent1 - tangent2
    sine_difference = math.sin(angle_difference)
    cosine_difference = math.cos(angle_difference)
    sine_twice_difference = math.sin(2.0 * angle_difference)
    cosine_twice_difference = math.cos(2.0 * angle_difference)

    denominator = 2.0 * mass1 + mass2 - mass2 * cosine_twice_difference
    tangent_denominator = (
        2.0 * mass2 * sine_twice_difference * tangent_angle_difference
    )

    first_inner = (
        length2 * omega2 * omega2
        + length1 * omega1 * omega1 * cosine_difference
    )
    tangent_first_inner = (
        2.0 * length2 * omega2 * tangent4
        + length1
        * (
            2.0 * omega1 * tangent3 * cosine_difference
            - omega1 * omega1 * sine_difference * tangent_angle_difference
        )
    )
    first_numerator = (
        -gravity * (2.0 * mass1 + mass2) * math.sin(theta1)
        - mass2 * gravity * math.sin(theta1 - 2.0 * theta2)
        - 2.0 * mass2 * sine_difference * first_inner
    )
    tangent_first_numerator = (
        -gravity * (2.0 * mass1 + mass2) * math.cos(theta1) * tangent1
        - mass2
        * gravity
        * math.cos(theta1 - 2.0 * theta2)
        * (tangent1 - 2.0 * tangent2)
        - 2.0
        * mass2
        * (
            cosine_difference * tangent_angle_difference * first_inner
            + sine_difference * tangent_first_inner
        )
    )
    first_denominator = length1 * denominator
    first_acceleration = first_numerator / first_denominator
    tangent_first_acceleration = (
        tangent_first_numerator * first_denominator
        - first_numerator * length1 * tangent_denominator
    ) / (first_denominator * first_denominator)

    second_inner = (
        length1 * omega1 * omega1 * (mass1 + mass2)
        + gravity * (mass1 + mass2) * math.cos(theta1)
        + length2 * mass2 * omega2 * omega2 * cosine_difference
    )
    tangent_second_inner = (
        2.0 * length1 * omega1 * tangent3 * (mass1 + mass2)
        - gravity * (mass1 + mass2) * math.sin(theta1) * tangent1
        + length2
        * mass2
        * (
            2.0 * omega2 * tangent4 * cosine_difference
            - omega2 * omega2 * sine_difference * tangent_angle_difference
        )
    )
    second_numerator = 2.0 * sine_difference * second_inner
    tangent_second_numerator = 2.0 * (
        cosine_difference * tangent_angle_difference * second_inner
        + sine_difference * tangent_second_inner
    )
    second_denominator = length2 * denominator
    second_acceleration = second_numerator / second_denominator
    tangent_second_acceleration = (
        tangent_second_numerator * second_denominator
        - second_numerator * length2 * tangent_denominator
    ) / (second_denominator * second_denominator)

    result = np.empty(8, dtype=np.float64)
    result[0] = omega1
    result[1] = omega2
    result[2] = first_acceleration
    result[3] = second_acceleration
    result[4] = tangent3
    result[5] = tangent4
    result[6] = tangent_first_acceleration
    result[7] = tangent_second_acceleration
    return result


def compiled_rhs(
    parameters: PendulumParameters,
) -> Callable[[float, np.ndarray], np.ndarray]:
    """Bind semantic parameter values around the low-level Numba kernel."""

    values = (
        parameters.length1,
        parameters.length2,
        parameters.mass1,
        parameters.mass2,
        parameters.gravity,
    )

    def evaluate(time_value: float, augmented: np.ndarray) -> np.ndarray:
        return compiled_reference_and_tangent_rhs(time_value, augmented, *values)

    return evaluate


def run_renormalized_tangent_compiled(
    spec: RenormalizedTangentSpec | None = None,
) -> RenormalizedTangentResult:
    """Run the accepted observable with the Numba-compiled augmented RHS."""

    spec = spec or RenormalizedTangentSpec()
    return _run_renormalized_tangent_with_rhs(spec, compiled_rhs(spec.parameters))


def evaluate_renormalized_tangent_compiled(
    spec: RenormalizedTangentSpec,
) -> RenormalizedTangentEvaluation:
    """Expose the compiled path through the established evaluator boundary."""

    return evaluate_renormalized_tangent_runner(
        spec,
        runner=run_renormalized_tangent_compiled,
        evaluator=COMPILED_EVALUATOR,
    )
