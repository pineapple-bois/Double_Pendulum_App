"""Lyapunov-specific adapter to the neutral scalar-evaluation boundary."""

from __future__ import annotations

import math
from time import perf_counter
from typing import Callable

if __package__:
    from .reference import (
        RenormalizedTangentDiagnostics,
        RenormalizedTangentResult,
        RenormalizedTangentSpec,
        run_renormalized_tangent,
    )
else:
    from reference import (
        RenormalizedTangentDiagnostics,
        RenormalizedTangentResult,
        RenormalizedTangentSpec,
        run_renormalized_tangent,
    )

from development.chaos_content.prototypes.state_space_fields import (
    EvaluationStatus,
    ScalarEvaluation,
)


REFERENCE_EVALUATOR = "numpy_scipy_reference"
RenormalizedTangentEvaluation = ScalarEvaluation[RenormalizedTangentDiagnostics]
RenormalizedTangentEvaluator = Callable[
    [RenormalizedTangentSpec], RenormalizedTangentEvaluation
]
RenormalizedTangentRunner = Callable[
    [RenormalizedTangentSpec], RenormalizedTangentResult
]


def evaluate_renormalized_tangent_reference(
    spec: RenormalizedTangentSpec,
) -> RenormalizedTangentEvaluation:
    """Adapt the trusted NumPy/SciPy result to one neutral scalar outcome.

    Only the reference evaluator's bounded numerical ``RuntimeError`` is
    represented as data. Programming and specification exceptions propagate.
    """

    return evaluate_renormalized_tangent_runner(
        spec,
        runner=run_renormalized_tangent,
        evaluator=REFERENCE_EVALUATOR,
    )


def evaluate_renormalized_tangent_runner(
    spec: RenormalizedTangentSpec,
    *,
    runner: RenormalizedTangentRunner,
    evaluator: str,
) -> RenormalizedTangentEvaluation:
    """Adapt one implementation of the observable to the shared outcome."""

    started = perf_counter()
    try:
        result = runner(spec)
    except RuntimeError as error:
        return ScalarEvaluation(
            status=EvaluationStatus.EXECUTION_ERROR,
            value=None,
            diagnostics=None,
            elapsed_seconds=perf_counter() - started,
            evaluator=evaluator,
            error_type=type(error).__name__,
            error_message=str(error),
        )

    diagnostics = result.diagnostics
    rate = result.finite_time_stretching_rate
    finite_rate = math.isfinite(rate)
    validity_issues = list(diagnostics.validity_issues)
    if not diagnostics.numerically_valid and not validity_issues:
        validity_issues.append("observable evaluator reported numerical invalidity")
    if not finite_rate:
        validity_issues.append("finite-time stretching rate was non-finite")
    return ScalarEvaluation(
        status=(
            EvaluationStatus.COMPLETED_VALID
            if diagnostics.numerically_valid and not validity_issues
            else EvaluationStatus.COMPLETED_INVALID
        ),
        value=rate if finite_rate else None,
        diagnostics=diagnostics,
        elapsed_seconds=perf_counter() - started,
        evaluator=evaluator,
        validity_issues=tuple(validity_issues),
    )
