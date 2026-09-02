"""Targeted recovery policy for the compiled finite-time evaluator."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, replace
from time import perf_counter
from typing import Callable

import numpy as np

if __package__:
    from .compiled import compiled_rhs, evaluate_renormalized_tangent_compiled
    from .evaluation import RenormalizedTangentEvaluation
    from .fortran_dop853 import (
        COMPILED_FORTRAN_EVALUATOR,
        _MAX_STEP_FLOATING_POINT_ALLOWANCE,
        _integrate_compiled_dop853_segment_unchecked,
        evaluate_renormalized_tangent_compiled_fortran,
    )
    from .reference import (
        RenormalizedTangentSpec,
        SolverSpec,
        _resolved_interval_max_step,
        _run_renormalized_tangent_with_rhs,
    )
else:
    from compiled import compiled_rhs, evaluate_renormalized_tangent_compiled
    from evaluation import RenormalizedTangentEvaluation
    from fortran_dop853 import (
        COMPILED_FORTRAN_EVALUATOR,
        _MAX_STEP_FLOATING_POINT_ALLOWANCE,
        _integrate_compiled_dop853_segment_unchecked,
        evaluate_renormalized_tangent_compiled_fortran,
    )
    from reference import (
        RenormalizedTangentSpec,
        SolverSpec,
        _resolved_interval_max_step,
        _run_renormalized_tangent_with_rhs,
    )

from development.chaos_content.prototypes.state_space_fields import EvaluationStatus


HYBRID_FAST_EVALUATOR = "compiled_dop853"
HYBRID_FALLBACK_EVALUATOR = "compiled_rhs_solve_ivp_fallback"
HYBRID_FAST_ERROR_EVALUATOR = "compiled_dop853_execution_error"
_ENDPOINT_SNAP_FACTOR = 1.01
_MAX_STEP_ERROR = re.compile(
    r"^Fortran DOP853 exceeded the declared max_step: "
    r"(?P<observed>[0-9eE+.-]+) > (?P<declared>[0-9eE+.-]+)\.$"
)


@dataclass(frozen=True)
class _SegmentStepObservation:
    segment_number: int
    maximum_gap: float
    violation_count: int
    violations_are_endpoint_only: bool


@dataclass(frozen=True)
class _EndpointMaxStepVerification:
    candidate_message_matched: bool
    verified: bool
    declared_max_step: float | None = None
    reported_maximum_gap: float | None = None
    violating_segment_numbers: tuple[int, ...] = ()


class _EndpointSnapVerifier:
    """Replay compiled DOP853 while observing, but not accepting, cap excess."""

    def __init__(self) -> None:
        self.observations: list[_SegmentStepObservation] = []

    def __call__(
        self,
        rhs: Callable[[float, np.ndarray], np.ndarray],
        initial: np.ndarray,
        requested: np.ndarray,
        solver: SolverSpec,
        max_step: float,
    ) -> tuple[np.ndarray, int]:
        segment = _integrate_compiled_dop853_segment_unchecked(
            rhs,
            initial,
            requested,
            solver,
            max_step,
        )
        gaps = np.diff(segment.time)
        allowance = _MAX_STEP_FLOATING_POINT_ALLOWANCE * max(
            1.0,
            abs(max_step),
        )
        violating_indices = np.flatnonzero(gaps > max_step + allowance)
        self.observations.append(
            _SegmentStepObservation(
                segment_number=len(self.observations) + 1,
                maximum_gap=float(np.max(gaps)),
                violation_count=len(violating_indices),
                violations_are_endpoint_only=bool(
                    len(violating_indices) == 1
                    and violating_indices[0] == len(gaps) - 1
                ),
            )
        )
        return segment.state, segment.function_evaluations


def _resolved_max_step(spec: RenormalizedTangentSpec) -> float:
    return _resolved_interval_max_step(
        spec.solver,
        spec.characteristic_length,
        spec.parameters.gravity,
        spec.renormalization_interval,
    )


def _candidate_endpoint_max_step_error(
    evaluation: RenormalizedTangentEvaluation,
    spec: RenormalizedTangentSpec,
) -> tuple[float, float] | None:
    if (
        evaluation.status is not EvaluationStatus.EXECUTION_ERROR
        or evaluation.evaluator != COMPILED_FORTRAN_EVALUATOR
        or evaluation.error_type != "RuntimeError"
        or evaluation.error_message is None
    ):
        return None
    match = _MAX_STEP_ERROR.fullmatch(evaluation.error_message)
    if match is None:
        return None
    observed = float(match.group("observed"))
    declared = float(match.group("declared"))
    expected = _resolved_max_step(spec)
    allowance = _MAX_STEP_FLOATING_POINT_ALLOWANCE * max(1.0, abs(expected))
    if (
        declared != expected
        or not math.isfinite(observed)
        or observed <= declared + allowance
        or observed > _ENDPOINT_SNAP_FACTOR * declared + allowance
    ):
        return None
    return observed, declared


def _verify_endpoint_max_step_incompatibility(
    evaluation: RenormalizedTangentEvaluation,
    spec: RenormalizedTangentSpec,
) -> _EndpointMaxStepVerification:
    candidate = _candidate_endpoint_max_step_error(evaluation, spec)
    if candidate is None:
        return _EndpointMaxStepVerification(False, False)
    reported_gap, declared = candidate
    verifier = _EndpointSnapVerifier()
    _run_renormalized_tangent_with_rhs(
        spec,
        compiled_rhs(spec.parameters),
        segment_solver=verifier,
    )

    violating = tuple(
        observation
        for observation in verifier.observations
        if observation.violation_count
    )
    allowance = _MAX_STEP_FLOATING_POINT_ALLOWANCE * max(1.0, abs(declared))
    verified = bool(
        violating
        and math.isclose(
            violating[0].maximum_gap,
            reported_gap,
            rel_tol=0.0,
            abs_tol=allowance,
        )
        and all(
            observation.violations_are_endpoint_only
            and observation.maximum_gap
            <= _ENDPOINT_SNAP_FACTOR * declared + allowance
            for observation in violating
        )
    )
    return _EndpointMaxStepVerification(
        candidate_message_matched=True,
        verified=verified,
        declared_max_step=declared,
        reported_maximum_gap=reported_gap,
        violating_segment_numbers=tuple(
            observation.segment_number for observation in violating
        ),
    )


def _with_hybrid_provenance(
    evaluation: RenormalizedTangentEvaluation,
    evaluator: str,
    started: float,
) -> RenormalizedTangentEvaluation:
    return replace(
        evaluation,
        elapsed_seconds=perf_counter() - started,
        evaluator=evaluator,
    )


def evaluate_renormalized_tangent_hybrid(
    spec: RenormalizedTangentSpec,
) -> RenormalizedTangentEvaluation:
    """Use compiled DOP853, falling back only after endpoint-snap verification."""

    started = perf_counter()
    fast = evaluate_renormalized_tangent_compiled_fortran(spec)
    if fast.status is not EvaluationStatus.EXECUTION_ERROR:
        return _with_hybrid_provenance(fast, HYBRID_FAST_EVALUATOR, started)

    verification = _verify_endpoint_max_step_incompatibility(fast, spec)
    if not verification.verified:
        return _with_hybrid_provenance(
            fast,
            HYBRID_FAST_ERROR_EVALUATOR,
            started,
        )

    fallback = evaluate_renormalized_tangent_compiled(spec)
    return _with_hybrid_provenance(
        fallback,
        HYBRID_FALLBACK_EVALUATOR,
        started,
    )
