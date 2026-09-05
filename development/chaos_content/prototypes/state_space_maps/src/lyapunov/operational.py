"""Operational S1 selection with the established hybrid as recovery authority."""

from __future__ import annotations

from dataclasses import replace
from time import perf_counter

import numpy as np

from ..state_space_fields import EvaluationStatus
from .compiled_equivalence import ENERGY_DIAGNOSTIC_ABSOLUTE_TOLERANCE
from .evaluation import RenormalizedTangentEvaluation
from .hybrid import evaluate_renormalized_tangent_hybrid
from .reference import RenormalizedTangentDiagnostics, RenormalizedTangentSpec
from .s1 import (
    S1_EVALUATOR,
    evaluate_renormalized_tangent_s1,
    s1_build_support,
    s1_specification_eligibility,
)


S1_RECOVERY_EXECUTION_ERROR = "s1_execution_error"
S1_RECOVERY_NUMERICAL_REJECTION = "s1_numerical_rejection"
S1_RECOVERY_BORDERLINE_DIAGNOSTIC = "s1_borderline_diagnostic"
S1_NORM_BORDERLINE_ABSOLUTE_TOLERANCE = 64.0 * np.finfo(float).eps


def _has_borderline_diagnostic(
    evaluation: RenormalizedTangentEvaluation,
    spec: RenormalizedTangentSpec,
) -> bool:
    diagnostics = evaluation.diagnostics
    if not isinstance(diagnostics, RenormalizedTangentDiagnostics):
        return True
    energy_distance = abs(
        diagnostics.maximum_normalized_reference_energy_drift
        - spec.energy_drift_limit
    )
    norm_distance = abs(
        diagnostics.maximum_post_renormalization_norm_error
        - spec.renormalization_norm_tolerance
    )
    return bool(
        energy_distance <= ENERGY_DIAGNOSTIC_ABSOLUTE_TOLERANCE
        or norm_distance <= S1_NORM_BORDERLINE_ABSOLUTE_TOLERANCE
    )


def _recovery_reason(
    candidate: RenormalizedTangentEvaluation,
    spec: RenormalizedTangentSpec,
) -> str | None:
    if candidate.status is EvaluationStatus.EXECUTION_ERROR:
        return S1_RECOVERY_EXECUTION_ERROR
    if _has_borderline_diagnostic(candidate, spec):
        return S1_RECOVERY_BORDERLINE_DIAGNOSTIC
    if candidate.status is EvaluationStatus.COMPLETED_INVALID:
        return S1_RECOVERY_NUMERICAL_REJECTION
    return None


def evaluate_renormalized_tangent_operational(
    spec: RenormalizedTangentSpec,
) -> RenormalizedTangentEvaluation:
    """Attempt S1 only when eligible; otherwise preserve the trusted hybrid."""

    eligibility = s1_specification_eligibility(spec)
    if not eligibility.eligible or not s1_build_support().supported:
        return evaluate_renormalized_tangent_hybrid(spec)

    started = perf_counter()
    candidate = evaluate_renormalized_tangent_s1(spec)
    recovery_reason = _recovery_reason(candidate, spec)
    if recovery_reason is None:
        return replace(candidate, elapsed_seconds=perf_counter() - started)

    recovered = evaluate_renormalized_tangent_hybrid(spec)
    return replace(
        recovered,
        elapsed_seconds=perf_counter() - started,
        attempted_evaluators=(*recovered.attempted_evaluators, S1_EVALUATOR),
        recovery_reason=recovery_reason,
        attempt_provenance={
            **recovered.attempt_provenance,
            S1_EVALUATOR: dict(candidate.implementation_provenance),
        },
    )
