"""Guarded S1 native single-cell Lyapunov implementation.

This is the operational copy of the validated S1 compiled loop.  It preserves
the validated equations, SciPy 1.18.0 DOP853 source, controller, observation,
renormalisation, and diagnostic policies. Immutable build products are shared
only through validated artifacts; runtime handles and state remain process-local.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from .evaluation import (
    RenormalizedTangentEvaluation,
    evaluate_renormalized_tangent_runner,
)
from .reference import (
    CandidateAMetric,
    PendulumParameters,
    RenormalizedTangentDiagnostics,
    RenormalizedTangentResult,
    RenormalizedTangentSpec,
    SolverSpec,
    _resolved_interval_max_step,
)
from .s1_artifacts import (
    S1_ARTIFACT_CACHE_ENVIRONMENT,
    S1_BUILD_FLAGS,
    S1_DOP_SOURCE_VERSION,
    S1_EVALUATOR,
    S1_NATIVE_DIRECTORY,
    S1_SOURCE_SHA256,
    S1Artifact,
    S1BuildSupport,
    S1NativeUnavailableError,
    _native_callbacks,
    _source_hashes,
    clear_s1_process_runtime,
    configure_s1_artifact,
    ensure_s1_artifact,
    load_s1_artifact,
    native_library,
    prepare_s1_artifact_for_workers,
    s1_artifact_cache_directory,
    s1_artifact_identity,
    s1_artifact_key,
    s1_build_provenance,
    s1_build_support,
    unavailable_s1_artifact,
)


S1_VALIDATED_DURATIONS = (1.0, 2.0, 5.0, 10.0, 20.0)


@dataclass(frozen=True)
class S1Eligibility:
    eligible: bool
    reasons: tuple[str, ...] = ()


def s1_specification_eligibility(spec: RenormalizedTangentSpec) -> S1Eligibility:
    """Constrain S1 to the initially validated standard periodic-field policy."""

    state = spec.initial_state.as_array()
    reasons: list[str] = []
    if not (-np.pi <= state[0] < np.pi and -np.pi <= state[1] < np.pi):
        reasons.append("initial angles are outside the validated [-pi, pi) chart")
    if not np.array_equal(state[2:], np.zeros(2)):
        reasons.append("initial angular velocities are not the validated zero values")
    if spec.parameters != PendulumParameters():
        reasons.append("physical parameters differ from the validated standard values")
    if spec.initial_tangent != (1.0, 0.0, 0.0, 0.0):
        reasons.append("initial tangent differs from the validated standard vector")
    if spec.duration not in S1_VALIDATED_DURATIONS:
        reasons.append("duration is outside the validated horizon allowlist")
    if spec.renormalization_interval != 0.25:
        reasons.append("renormalisation interval differs from 0.25 seconds")
    if spec.sampling_interval != 0.01:
        reasons.append("sampling interval differs from 0.01 seconds")
    if spec.energy_drift_limit != 1.0e-7:
        reasons.append("energy-drift limit differs from the validated standard limit")
    if spec.renormalization_norm_tolerance != 1.0e-12:
        reasons.append("reset-norm limit differs from the validated standard limit")
    if spec.characteristic_length != 1.0:
        reasons.append("characteristic length differs from the validated standard value")
    if spec.solver != SolverSpec():
        reasons.append("solver configuration differs from the validated standard policy")
    return S1Eligibility(eligible=not reasons, reasons=tuple(reasons))


def run_renormalized_tangent_s1(
    spec: RenormalizedTangentSpec,
) -> RenormalizedTangentResult:
    """Run one S1 cell without eligibility selection or recovery routing."""

    if spec.solver.method.upper() != "DOP853":
        raise ValueError("S1 requires DOP853.")
    metric = CandidateAMetric(spec.characteristic_length, spec.parameters.gravity)
    initial = np.asarray(spec.initial_tangent, dtype=float)
    initial_unit = initial / float(metric.tangent_norm(initial))
    state = np.concatenate((spec.initial_state.as_array(), initial_unit))
    parameters = spec.parameters
    native_parameters = np.array(
        [
            parameters.length1,
            parameters.length2,
            parameters.mass1,
            parameters.mass2,
            parameters.gravity,
        ]
    )
    cycles = int(round(spec.duration / spec.renormalization_interval))
    boundaries = np.linspace(0.0, spec.duration, cycles + 1)
    max_step = _resolved_interval_max_step(
        spec.solver,
        spec.characteristic_length,
        parameters.gravity,
        spec.renormalization_interval,
    )
    output = np.empty((cycles, 4))
    stats = np.zeros(4)
    rhs, reset = _native_callbacks()
    code = native_library().s1_loop(
        rhs.address,
        reset.address,
        state,
        native_parameters,
        boundaries,
        cycles,
        spec.solver.rtol,
        spec.solver.atol,
        max_step,
        metric.characteristic_time,
        output,
        stats,
    )
    if code == 40:
        raise RuntimeError(
            "compiled DOP853 exceeded the declared max_step: "
            f"{stats[2]} > {max_step}."
        )
    if code:
        raise RuntimeError(f"S1 native loop failed with status {code}.")
    issues: list[str] = []
    if stats[0] > spec.energy_drift_limit:
        issues.append("reference energy drift exceeded its declared limit")
    if stats[1] > spec.renormalization_norm_tolerance:
        issues.append(
            "post-renormalization Candidate-A norm error exceeded its limit"
        )
    diagnostics = RenormalizedTangentDiagnostics(
        maximum_normalized_reference_energy_drift=float(stats[0]),
        maximum_post_renormalization_norm_error=float(stats[1]),
        max_step_seconds=max_step,
        segment_count=cycles,
        solver_function_evaluations=int(stats[3]),
        numerically_valid=not issues,
        validity_issues=tuple(issues),
    )
    return RenormalizedTangentResult(
        spec=spec,
        metric=metric,
        initial_unit_tangent=initial_unit,
        cycle_end_time=boundaries[1:],
        stretch_factor=output[:, 0].copy(),
        log_stretch_increment=output[:, 1].copy(),
        cumulative_log_stretch=output[:, 2].copy(),
        cumulative_finite_time_rate=output[:, 3].copy(),
        final_reference_state=state[:4].copy(),
        final_unit_tangent=state[4:].copy(),
        diagnostics=diagnostics,
    )


def evaluate_renormalized_tangent_s1(
    spec: RenormalizedTangentSpec,
) -> RenormalizedTangentEvaluation:
    """Adapt S1 to the shared scalar result without performing recovery."""

    evaluation = evaluate_renormalized_tangent_runner(
        spec,
        runner=run_renormalized_tangent_s1,
        evaluator=S1_EVALUATOR,
    )
    return replace(
        evaluation,
        implementation_provenance=s1_build_provenance(runtime_artifact=True),
    )
