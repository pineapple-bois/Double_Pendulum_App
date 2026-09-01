"""Validated compiled-Fortran integration for the finite-time observable.

Experiment 015 earned this one narrow replacement for the Python ``solve_ivp``
segment boundary.  The Numba Euler--Lagrange RHS/JVP, shared Candidate-A
renormalisation driver, result contracts, and numerical-validity limits remain
unchanged.  The reference and compiled-RHS ``solve_ivp`` runners remain the
scientific oracle paths.
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy.integrate import ode

if __package__:
    from .compiled import compiled_rhs
    from .evaluation import (
        RenormalizedTangentEvaluation,
        evaluate_renormalized_tangent_runner,
    )
    from .reference import (
        RenormalizedTangentResult,
        RenormalizedTangentSpec,
        SolverSpec,
        _run_renormalized_tangent_with_rhs,
    )
else:
    from compiled import compiled_rhs
    from evaluation import (
        RenormalizedTangentEvaluation,
        evaluate_renormalized_tangent_runner,
    )
    from reference import (
        RenormalizedTangentResult,
        RenormalizedTangentSpec,
        SolverSpec,
        _run_renormalized_tangent_with_rhs,
    )


COMPILED_FORTRAN_EVALUATOR = "numba_rhs_fortran_dop853"
_TIME_ABSOLUTE_TOLERANCE = 1.0e-13
_MAX_STEP_FLOATING_POINT_ALLOWANCE = 64.0 * np.finfo(float).eps
_MAX_INTERNAL_STEPS = 100_000


@dataclass(frozen=True)
class _AcceptedStepSegment:
    """Internal accepted-step trajectory returned by one Fortran segment."""

    time: np.ndarray
    state: np.ndarray
    function_evaluations: int
    return_code: int | None
    warning_messages: tuple[str, ...]


def _integrate_fortran_dop853_segment(
    rhs: Callable[[float, np.ndarray], np.ndarray],
    initial: np.ndarray,
    requested: np.ndarray,
    solver: SolverSpec,
    max_step: float,
) -> _AcceptedStepSegment:
    """Integrate one renormalisation segment and observe accepted steps."""

    if solver.method.upper() != "DOP853":
        raise ValueError("The compiled Fortran path supports only DOP853.")

    initial = np.asarray(initial, dtype=float)
    requested = np.asarray(requested, dtype=float)
    if initial.ndim != 1 or not np.all(np.isfinite(initial)):
        raise ValueError("The segment initial state must be a finite vector.")
    if (
        requested.ndim != 1
        or len(requested) < 2
        or not np.all(np.isfinite(requested))
        or not np.all(np.diff(requested) > 0.0)
    ):
        raise ValueError("Requested segment times must be finite and increasing.")
    if not math.isfinite(max_step) or max_step <= 0.0:
        raise ValueError("max_step must be positive and finite.")

    start = float(requested[0])
    end = float(requested[-1])
    accepted_times: list[float] = []
    accepted_states: list[np.ndarray] = []
    function_evaluations = 0

    def counted_rhs(time_value: float, state: np.ndarray) -> np.ndarray:
        nonlocal function_evaluations
        function_evaluations += 1
        return rhs(time_value, state)

    def observe(time_value: float, state: np.ndarray) -> int:
        accepted_times.append(float(time_value))
        accepted_states.append(np.asarray(state, dtype=float).copy())
        return 0

    integrator = ode(counted_rhs).set_integrator(
        "dop853",
        rtol=solver.rtol,
        atol=solver.atol,
        max_step=max_step,
        nsteps=_MAX_INTERNAL_STEPS,
        verbosity=-1,
    )
    integrator.set_solout(observe)
    integrator.set_initial_value(initial, start)
    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter("always")
        final_state = np.asarray(integrator.integrate(end), dtype=float)
    return_code = integrator.get_return_code()
    warning_messages = tuple(str(item.message) for item in caught_warnings)

    if not integrator.successful() or return_code != 1:
        warning_suffix = (
            f" Warnings: {'; '.join(warning_messages)}" if warning_messages else ""
        )
        raise RuntimeError(
            "Fortran DOP853 failed on "
            f"[{start}, {end}] with return code {return_code}.{warning_suffix}"
        )
    if final_state.shape != initial.shape or not np.all(np.isfinite(final_state)):
        raise RuntimeError("Fortran DOP853 returned a non-finite or malformed state.")
    if not math.isclose(
        float(integrator.t),
        end,
        rel_tol=0.0,
        abs_tol=_TIME_ABSOLUTE_TOLERANCE,
    ):
        raise RuntimeError(
            "Fortran DOP853 did not reach the requested segment endpoint: "
            f"{integrator.t} != {end}."
        )

    if not accepted_times or not math.isclose(
        accepted_times[0],
        start,
        rel_tol=0.0,
        abs_tol=_TIME_ABSOLUTE_TOLERANCE,
    ):
        accepted_times.insert(0, start)
        accepted_states.insert(0, initial.copy())
    if not math.isclose(
        accepted_times[-1],
        end,
        rel_tol=0.0,
        abs_tol=_TIME_ABSOLUTE_TOLERANCE,
    ):
        accepted_times.append(end)
        accepted_states.append(final_state.copy())

    time = np.asarray(accepted_times, dtype=float)
    state = np.asarray(accepted_states, dtype=float)
    if (
        time.ndim != 1
        or state.shape != (len(time), len(initial))
        or not np.all(np.isfinite(time))
        or not np.all(np.isfinite(state))
        or not np.all(np.diff(time) > 0.0)
    ):
        raise RuntimeError("Fortran DOP853 accepted-step output is invalid.")
    maximum_step_gap = float(np.max(np.diff(time)))
    allowed_max_step = max_step + _MAX_STEP_FLOATING_POINT_ALLOWANCE * max(
        1.0, abs(max_step)
    )
    if maximum_step_gap > allowed_max_step:
        raise RuntimeError(
            "Fortran DOP853 exceeded the declared max_step: "
            f"{maximum_step_gap} > {max_step}."
        )

    return _AcceptedStepSegment(
        time=time,
        state=state,
        function_evaluations=function_evaluations,
        return_code=return_code,
        warning_messages=warning_messages,
    )


def _solve_fortran_dop853_segment(
    rhs: Callable[[float, np.ndarray], np.ndarray],
    initial: np.ndarray,
    requested: np.ndarray,
    solver: SolverSpec,
    max_step: float,
) -> tuple[np.ndarray, int]:
    segment = _integrate_fortran_dop853_segment(
        rhs,
        initial,
        requested,
        solver,
        max_step,
    )
    return segment.state, segment.function_evaluations


def run_renormalized_tangent_compiled_fortran(
    spec: RenormalizedTangentSpec | None = None,
) -> RenormalizedTangentResult:
    """Run the accepted observable with Numba RHS/JVP and Fortran DOP853."""

    spec = spec or RenormalizedTangentSpec()
    return _run_renormalized_tangent_with_rhs(
        spec,
        compiled_rhs(spec.parameters),
        segment_solver=_solve_fortran_dop853_segment,
    )


def evaluate_renormalized_tangent_compiled_fortran(
    spec: RenormalizedTangentSpec,
) -> RenormalizedTangentEvaluation:
    """Expose the promoted path through the established evaluator boundary."""

    return evaluate_renormalized_tangent_runner(
        spec,
        runner=run_renormalized_tangent_compiled_fortran,
        evaluator=COMPILED_FORTRAN_EVALUATOR,
    )
