"""Isolate Experiment 007 tangent/QR policies on one common reference history."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

RUNTIME_CACHE_ROOT = Path(tempfile.gettempdir()) / "double-pendulum-chaos-cache"
RUNTIME_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(RUNTIME_CACHE_ROOT / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(RUNTIME_CACHE_ROOT / "xdg"))

EXPERIMENT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
EXPERIMENT_007_ROOT = EXPERIMENT_ROOT.parent / "007_full_matrix_qr_tangent_dynamics"
for import_root in (REPOSITORY_ROOT, EXPERIMENT_007_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

import numpy as np
from scipy.integrate import solve_ivp

import full_matrix_qr_tangent_dynamics as experiment007


experiment006 = experiment007.experiment006
SolverPolicy = type(experiment007.SOLVER_POLICY)

EXPERIMENT_NAME = "common_reference_qr_isolation"
DURATION_SECONDS = 80.0
REFERENCE_SEGMENT_SECONDS = 0.125
COMMON_REFERENCE_POLICY = experiment007.STRICTER_POLICY
COMMON_REFERENCE_MAX_STEP = experiment007.HALF_MAX_STEP_SECONDS
REFERENCE_VALIDATION_POLICY = SolverPolicy(
    name="common_reference_local_refinement",
    method="DOP853",
    rtol=1.0e-12,
    atol=1.0e-14,
    role="Experiment 008 local dense-reference validation",
)
REFERENCE_VALIDATION_MAX_STEP = COMMON_REFERENCE_MAX_STEP / 2.0
REFERENCE_LOCAL_ERROR_LIMIT = 1.0e-8
REFERENCE_ENERGY_DRIFT_LIMIT = experiment007.ENERGY_DRIFT_LIMIT

BASELINE_QR_INTERVAL = experiment007.QR_INTERVAL_SECONDS
SHORT_QR_INTERVAL = experiment007.SHORT_QR_INTERVAL_SECONDS
LONG_QR_INTERVAL = experiment007.LONG_QR_INTERVAL_SECONDS
BASELINE_TANGENT_POLICY = experiment007.SOLVER_POLICY
STRICT_TANGENT_POLICY = experiment007.STRICTER_POLICY
BASELINE_TANGENT_MAX_STEP = experiment007.MAX_STEP_SECONDS
HALF_TANGENT_MAX_STEP = experiment007.HALF_MAX_STEP_SECONDS

STRICT_DIFFERENCE_LIMIT = experiment007.MAX_TOLERANCE_SPECTRUM_DIFFERENCE_PER_SECOND
HALF_STEP_DIFFERENCE_LIMIT = experiment007.MAX_STEP_SPECTRUM_DIFFERENCE_PER_SECOND
QR_INTERVAL_DIFFERENCE_LIMIT = experiment007.MAX_QR_INTERVAL_SPECTRUM_DIFFERENCE_PER_SECOND
COLLAPSE_RATIO_LIMIT = 0.25
MATERIAL_REMAINDER_RATIO = 0.50
LATE_WINDOW_START_SECONDS = 60.0
COMMON_COMPARISON_INTERVAL_SECONDS = 0.5

EXPERIMENT_007_SEPARATIONS = {
    "strict_tangent": 0.08183219759628324,
    "half_tangent_step": 0.15677095575985878,
    "short_qr_interval": 0.14961110705931913,
    "long_qr_interval": 0.10273236233883432,
}


@dataclass(frozen=True)
class ReferenceSegment:
    start_time: float
    end_time: float
    start_state: np.ndarray
    end_state: np.ndarray
    dense_solution: Callable[[float | np.ndarray], np.ndarray]
    solver_status: dict[str, Any]
    local_midpoint_error: float
    local_endpoint_error: float
    maximum_energy_drift: float


class CommonReferenceHistory:
    """Piecewise-dense, locally rebased reference independent of tangent runs."""

    def __init__(
        self,
        segments: list[ReferenceSegment],
        *,
        duration: float,
        public_summary: dict[str, Any],
        sample_time: np.ndarray,
        sample_state: np.ndarray,
        sample_energy_drift: np.ndarray,
    ) -> None:
        if not segments:
            raise ValueError("Common reference history requires at least one segment.")
        self.segments = segments
        self.duration = duration
        self.public_summary = public_summary
        self.sample_time = sample_time
        self.sample_state = sample_state
        self.sample_energy_drift = sample_energy_drift
        self._end_times = np.asarray([segment.end_time for segment in segments])

    def segment_index(self, time_value: float) -> int:
        if time_value < -1.0e-13 or time_value > self.duration + 1.0e-13:
            raise ValueError(f"Reference query {time_value} lies outside the history.")
        index = int(np.searchsorted(self._end_times, time_value, side="right"))
        return min(max(index, 0), len(self.segments) - 1)

    def evaluate(self, time_value: float) -> np.ndarray:
        segment = self.segments[self.segment_index(float(time_value))]
        state = np.asarray(segment.dense_solution(float(time_value)), dtype=float)
        return experiment006.canonicalize_state_angles(state)


def _solve_reference_segment(
    dynamics: Any,
    start: float,
    end: float,
    initial_state: np.ndarray,
    policy: Any,
    max_step: float,
    *,
    dense_output: bool,
    t_eval: np.ndarray | None = None,
) -> Any:
    return solve_ivp(
        lambda time_value, state: dynamics.flow(state, time_value),
        (start, end),
        np.asarray(initial_state, dtype=float),
        method=policy.method,
        rtol=policy.rtol,
        atol=policy.atol,
        max_step=max_step,
        dense_output=dense_output,
        t_eval=t_eval,
    )


def build_common_reference_history(
    dynamics: Any,
    *,
    duration: float = DURATION_SECONDS,
    segment_interval: float = REFERENCE_SEGMENT_SECONDS,
) -> CommonReferenceHistory:
    boundaries = experiment007.deterministic_cycle_times(duration, segment_interval)
    current_state = np.array(experiment006.BASE_STATE_RADIANS, copy=True)
    initial_energy = float(experiment006.simple_energy(current_state))
    segments: list[ReferenceSegment] = []
    public_segments: list[dict[str, Any]] = []
    stored_times: list[np.ndarray] = []
    stored_states: list[np.ndarray] = []
    stored_energy_drifts: list[np.ndarray] = []

    for segment_index, (start, end) in enumerate(
        zip(boundaries[:-1], boundaries[1:]), start=1
    ):
        start = float(start)
        end = float(end)
        start_state = np.array(current_state, copy=True)
        common = _solve_reference_segment(
            dynamics,
            start,
            end,
            start_state,
            COMMON_REFERENCE_POLICY,
            COMMON_REFERENCE_MAX_STEP,
            dense_output=True,
        )
        if not common.success or common.sol is None or not np.all(np.isfinite(common.y)):
            raise RuntimeError(f"Common reference segment {segment_index} failed.")

        midpoint = 0.5 * (start + end)
        validation_times = np.asarray([midpoint, end])
        refined = _solve_reference_segment(
            dynamics,
            start,
            end,
            start_state,
            REFERENCE_VALIDATION_POLICY,
            REFERENCE_VALIDATION_MAX_STEP,
            dense_output=False,
            t_eval=validation_times,
        )
        if (
            not refined.success
            or refined.y.shape != (4, 2)
            or not np.all(np.isfinite(refined.y))
        ):
            raise RuntimeError(f"Reference validation segment {segment_index} failed.")

        common_validation = np.asarray(common.sol(validation_times), dtype=float).T
        refined_validation = np.asarray(refined.y, dtype=float).T
        validation_errors = []
        for common_state, refined_state in zip(
            common_validation, refined_validation
        ):
            difference = experiment006.wrapped_el_difference(
                common_state, refined_state
            )
            validation_errors.append(
                float(experiment006.candidate_a_norm(difference))
            )

        sample_count = int(round((end - start) / experiment007.OUTPUT_INTERVAL_SECONDS)) + 1
        sample_time = np.linspace(start, end, sample_count)
        sample_state = np.asarray(common.sol(sample_time), dtype=float).T
        sample_energy = experiment006.simple_energy(sample_state)
        sample_energy_drift = np.abs(sample_energy - initial_energy) / experiment006.energy_scale()
        maximum_energy_drift = float(np.max(sample_energy_drift))
        raw_end_state = np.asarray(common.y[:, -1], dtype=float)
        end_state = experiment006.canonicalize_state_angles(raw_end_state)
        solver_status = {
            "success": bool(common.success),
            "message": str(common.message),
            "nfev": int(common.nfev),
            "njev": int(common.njev),
            "nlu": int(common.nlu),
            "validation_success": bool(refined.success),
            "validation_nfev": int(refined.nfev),
        }
        segment = ReferenceSegment(
            start_time=start,
            end_time=end,
            start_state=start_state,
            end_state=end_state,
            dense_solution=common.sol,
            solver_status=solver_status,
            local_midpoint_error=validation_errors[0],
            local_endpoint_error=validation_errors[1],
            maximum_energy_drift=maximum_energy_drift,
        )
        segments.append(segment)
        public_segments.append(
            {
                "segment_index": segment_index,
                "start_time_seconds": start,
                "end_time_seconds": end,
                "start_state": start_state.tolist(),
                "end_state": end_state.tolist(),
                "local_midpoint_candidate_a_error": validation_errors[0],
                "local_endpoint_candidate_a_error": validation_errors[1],
                "maximum_normalized_energy_drift": maximum_energy_drift,
                "solver_status": solver_status,
            }
        )
        if segment_index > 1:
            sample_time = sample_time[1:]
            sample_state = sample_state[1:]
            sample_energy_drift = sample_energy_drift[1:]
        stored_times.append(sample_time)
        stored_states.append(experiment006.canonicalize_state_angles(sample_state))
        stored_energy_drifts.append(sample_energy_drift)
        current_state = end_state

    all_time = np.concatenate(stored_times)
    all_state = np.concatenate(stored_states)
    all_energy_drift = np.concatenate(stored_energy_drifts)
    maximum_local_error = max(
        max(segment.local_midpoint_error, segment.local_endpoint_error)
        for segment in segments
    )
    maximum_energy_drift = float(np.max(all_energy_drift))
    checks = {
        "all_common_and_validation_segments_succeeded": all(
            segment.solver_status["success"]
            and segment.solver_status["validation_success"]
            for segment in segments
        ),
        "local_dense_reference_error_within_1e-8": bool(
            maximum_local_error <= REFERENCE_LOCAL_ERROR_LIMIT
        ),
        "reference_energy_drift_within_1e-7": bool(
            maximum_energy_drift <= REFERENCE_ENERGY_DRIFT_LIMIT
        ),
        "sample_times_strictly_monotonic": bool(np.all(np.diff(all_time) > 0.0)),
        "sample_endpoints_complete": bool(
            math.isclose(all_time[0], 0.0, abs_tol=1.0e-13)
            and math.isclose(all_time[-1], duration, abs_tol=1.0e-13)
        ),
    }
    public_summary = {
        "accepted": all(checks.values()),
        "checks": checks,
        "duration_seconds": duration,
        "segment_interval_seconds": segment_interval,
        "segment_count": len(segments),
        "construction_policy": experiment006.policy_dict(COMMON_REFERENCE_POLICY),
        "construction_max_step_seconds": COMMON_REFERENCE_MAX_STEP,
        "validation_policy": experiment006.policy_dict(REFERENCE_VALIDATION_POLICY),
        "validation_max_step_seconds": REFERENCE_VALIDATION_MAX_STEP,
        "maximum_local_candidate_a_error": maximum_local_error,
        "maximum_normalized_energy_drift": maximum_energy_drift,
        "solver_statistics": {
            "common_nfev": int(sum(segment.solver_status["nfev"] for segment in segments)),
            "validation_nfev": int(
                sum(segment.solver_status["validation_nfev"] for segment in segments)
            ),
        },
        "final_state": segments[-1].end_state.tolist(),
        "segments": public_segments,
    }
    return CommonReferenceHistory(
        segments,
        duration=duration,
        public_summary=public_summary,
        sample_time=all_time,
        sample_state=all_state,
        sample_energy_drift=all_energy_drift,
    )


def tangent_matrix_rhs(
    dynamics: Any,
    reference_history: CommonReferenceHistory,
    time_value: float,
    tangent_flat: np.ndarray,
) -> np.ndarray:
    tangent_matrix = np.asarray(tangent_flat, dtype=float).reshape(4, 4)
    reference = reference_history.evaluate(time_value)
    return (dynamics.jacobian(reference, time_value) @ tangent_matrix).reshape(16)


def run_common_reference_qr(
    dynamics: Any,
    reference_history: CommonReferenceHistory,
    *,
    run_id: str,
    duration: float = DURATION_SECONDS,
    qr_interval: float = BASELINE_QR_INTERVAL,
    policy: Any = BASELINE_TANGENT_POLICY,
    max_step: float = BASELINE_TANGENT_MAX_STEP,
) -> dict[str, Any]:
    boundaries = experiment007.deterministic_cycle_times(duration, qr_interval)
    tangent = experiment007.initial_physical_tangent_basis()
    cumulative_logs = np.zeros(4)
    cycles: list[dict[str, Any]] = []
    solver_statuses: list[dict[str, Any]] = []

    for cycle_index, (start, end) in enumerate(
        zip(boundaries[:-1], boundaries[1:]), start=1
    ):
        start = float(start)
        end = float(end)
        tangent_start = np.array(tangent, copy=True)
        segment = experiment006.solve_one_segment(
            lambda time_value, flat: tangent_matrix_rhs(
                dynamics, reference_history, time_value, flat
            ),
            tangent_start.reshape(16),
            np.asarray([start, end]),
            policy,
            max_step=max_step,
        )
        solver_status = segment["solver_status"] | {"accepted": segment["accepted"]}
        solver_statuses.append(solver_status)
        if not segment["accepted"]:
            raise RuntimeError(f"Tangent QR cycle {cycle_index} failed.")
        tangent_pre = np.asarray(segment["state"][-1], dtype=float).reshape(4, 4)
        reset = experiment007.qr_reset(tangent_pre)
        cycle_logs = np.asarray(reset["log_diagonal"], dtype=float)
        cumulative_logs = cumulative_logs + cycle_logs
        spectrum = cumulative_logs / end
        checks = {
            "solver_segment_valid": segment["accepted"],
            "qr_reset_valid": reset["accepted"],
            "finite_accumulation": bool(
                np.all(np.isfinite(cycle_logs))
                and np.all(np.isfinite(cumulative_logs))
                and np.all(np.isfinite(spectrum))
            ),
        }
        cycles.append(
            {
                "cycle_index": cycle_index,
                "start_time_seconds": start,
                "end_time_seconds": end,
                "accepted": all(checks.values()),
                "checks": checks,
                "cycle_log_growth": cycle_logs.tolist(),
                "cumulative_log_growth": cumulative_logs.tolist(),
                "cumulative_finite_time_spectrum_per_second": spectrum.tolist(),
                "q_orthonormality_error": reset["orthonormality_error"],
                "scaled_reconstruction_relative_error": reset[
                    "scaled_reconstruction_relative_error"
                ],
                "physical_reconstruction_relative_error": reset[
                    "physical_reconstruction_relative_error"
                ],
                "post_metric_orthonormality_error": reset[
                    "post_metric_orthonormality_error"
                ],
                "reset_map_error": reset["reset_map_error"],
                "pre_qr_condition_number": reset["pre_qr_condition_number"],
                "r_diagonal": reset["diagonal"].tolist(),
                "solver_status": solver_status,
            }
        )
        tangent = reset["tangent_matrix_post"]

    cycle_logs_array = np.asarray([cycle["cycle_log_growth"] for cycle in cycles])
    stored_cumulative = np.asarray(
        [cycle["cumulative_log_growth"] for cycle in cycles]
    )
    end_times = np.asarray([cycle["end_time_seconds"] for cycle in cycles])
    stored_spectrum = np.asarray(
        [cycle["cumulative_finite_time_spectrum_per_second"] for cycle in cycles]
    )
    recomputed_cumulative = np.cumsum(cycle_logs_array, axis=0)
    cumulative_error = float(np.max(np.abs(recomputed_cumulative - stored_cumulative)))
    spectrum_error = float(
        np.max(np.abs(recomputed_cumulative / end_times[:, None] - stored_spectrum))
    )
    checks = {
        "common_reference_valid": reference_history.public_summary["accepted"],
        "all_cycles_accepted": all(cycle["accepted"] for cycle in cycles),
        "cumulative_bookkeeping_within_limit": bool(
            cumulative_error <= experiment007.BOOKKEEPING_ERROR_LIMIT
        ),
        "spectrum_bookkeeping_within_limit": bool(
            spectrum_error <= experiment007.BOOKKEEPING_ERROR_LIMIT
        ),
    }
    return {
        "run_id": run_id,
        "accepted": all(checks.values()),
        "checks": checks,
        "duration_seconds": duration,
        "qr_interval_seconds": qr_interval,
        "solver_policy": experiment006.policy_dict(policy),
        "max_step_seconds": max_step,
        "cycle_count": len(cycles),
        "cycles": cycles,
        "final_cumulative_log_growth": stored_cumulative[-1].tolist(),
        "final_diagnostic_spectrum_per_second": stored_spectrum[-1].tolist(),
        "maximum_q_orthonormality_error": max(
            cycle["q_orthonormality_error"] for cycle in cycles
        ),
        "maximum_physical_reconstruction_relative_error": max(
            cycle["physical_reconstruction_relative_error"] for cycle in cycles
        ),
        "minimum_r_diagonal": min(min(cycle["r_diagonal"]) for cycle in cycles),
        "maximum_pre_qr_condition_number": max(
            cycle["pre_qr_condition_number"] for cycle in cycles
        ),
        "cumulative_bookkeeping_error": cumulative_error,
        "spectrum_bookkeeping_error": spectrum_error,
        "solver_statistics": {
            "segments": len(solver_statuses),
            "nfev": int(sum(status["nfev"] for status in solver_statuses)),
            "all_segments_accepted": all(status["accepted"] for status in solver_statuses),
        },
        "_cycle_logs": cycle_logs_array,
        "_cumulative_logs": stored_cumulative,
        "_finite_time_spectrum": stored_spectrum,
    }


def public_run_summary(run: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in run.items()
        if not key.startswith("_") and key != "cycles"
    }


def common_comparison_times(duration: float) -> np.ndarray:
    first = math.ceil(LATE_WINDOW_START_SECONDS / COMMON_COMPARISON_INTERVAL_SECONDS)
    last = int(round(duration / COMMON_COMPARISON_INTERVAL_SECONDS))
    return np.arange(first, last + 1, dtype=float) * COMMON_COMPARISON_INTERVAL_SECONDS


def compare_common_reference_runs(
    baseline: dict[str, Any],
    comparison: dict[str, Any],
    *,
    difference_limit: float,
    experiment_007_separation: float,
) -> dict[str, Any]:
    final_baseline = np.asarray(baseline["final_diagnostic_spectrum_per_second"])
    final_comparison = np.asarray(comparison["final_diagnostic_spectrum_per_second"])
    final_component_difference = np.abs(final_comparison - final_baseline)
    final_maximum = float(np.max(final_component_difference))
    late_differences = []
    for time_value in common_comparison_times(baseline["duration_seconds"]):
        baseline_value = experiment007.spectrum_at_time(baseline, float(time_value))
        comparison_value = experiment007.spectrum_at_time(comparison, float(time_value))
        late_differences.append(np.abs(comparison_value - baseline_value))
    late_array = np.asarray(late_differences)
    late_maximum = float(np.max(late_array))
    final_ratio = final_maximum / experiment_007_separation
    late_ratio = late_maximum / experiment_007_separation
    checks = {
        "comparison_run_valid": comparison["accepted"],
        "final_difference_within_limit": bool(final_maximum <= difference_limit),
        "late_window_difference_within_limit": bool(late_maximum <= difference_limit),
        "final_separation_ratio_at_most_0.25": bool(
            final_ratio <= COLLAPSE_RATIO_LIMIT
        ),
    }
    return {
        "accepted_for_collapse": all(checks.values()),
        "checks": checks,
        "difference_limit_per_second": difference_limit,
        "experiment_007_separation_per_second": experiment_007_separation,
        "final_spectrum_per_second": final_comparison.tolist(),
        "final_component_differences_per_second": final_component_difference.tolist(),
        "final_maximum_difference_per_second": final_maximum,
        "late_window_maximum_difference_per_second": late_maximum,
        "final_separation_ratio": final_ratio,
        "late_window_separation_ratio": late_ratio,
    }


def classify_isolation(
    *,
    validity_accepted: bool,
    comparisons: dict[str, dict[str, Any]],
) -> str:
    if not validity_accepted:
        return "isolation_numerically_unresolved"
    if all(comparison["accepted_for_collapse"] for comparison in comparisons.values()):
        return "reference_shadow_divergence_primary_observed_source"
    material_remainder = any(
        (
            comparison["final_maximum_difference_per_second"]
            > comparison["difference_limit_per_second"]
            and comparison["final_separation_ratio"] >= MATERIAL_REMAINDER_RATIO
        )
        or (
            comparison["late_window_maximum_difference_per_second"]
            > comparison["difference_limit_per_second"]
            and comparison["late_window_separation_ratio"]
            >= MATERIAL_REMAINDER_RATIO
        )
        for comparison in comparisons.values()
    )
    if material_remainder:
        return "material_tangent_or_qr_policy_dependence_remains"
    return "isolation_numerically_unresolved"


def run_investigation(*, duration: float = DURATION_SECONDS) -> dict[str, Any]:
    dynamics = experiment006.VariationalDynamics()
    reference = build_common_reference_history(dynamics, duration=duration)
    run_specs = {
        "baseline": (
            BASELINE_TANGENT_POLICY,
            BASELINE_TANGENT_MAX_STEP,
            BASELINE_QR_INTERVAL,
        ),
        "strict_tangent": (
            STRICT_TANGENT_POLICY,
            BASELINE_TANGENT_MAX_STEP,
            BASELINE_QR_INTERVAL,
        ),
        "half_tangent_step": (
            BASELINE_TANGENT_POLICY,
            HALF_TANGENT_MAX_STEP,
            BASELINE_QR_INTERVAL,
        ),
        "short_qr_interval": (
            BASELINE_TANGENT_POLICY,
            BASELINE_TANGENT_MAX_STEP,
            SHORT_QR_INTERVAL,
        ),
        "long_qr_interval": (
            BASELINE_TANGENT_POLICY,
            BASELINE_TANGENT_MAX_STEP,
            LONG_QR_INTERVAL,
        ),
    }
    runs = {
        name: run_common_reference_qr(
            dynamics,
            reference,
            run_id=name,
            duration=duration,
            qr_interval=qr_interval,
            policy=policy,
            max_step=max_step,
        )
        for name, (policy, max_step, qr_interval) in run_specs.items()
    }
    comparison_limits = {
        "strict_tangent": STRICT_DIFFERENCE_LIMIT,
        "half_tangent_step": HALF_STEP_DIFFERENCE_LIMIT,
        "short_qr_interval": QR_INTERVAL_DIFFERENCE_LIMIT,
        "long_qr_interval": QR_INTERVAL_DIFFERENCE_LIMIT,
    }
    comparisons = {
        name: compare_common_reference_runs(
            runs["baseline"],
            runs[name],
            difference_limit=comparison_limits[name],
            experiment_007_separation=EXPERIMENT_007_SEPARATIONS[name],
        )
        for name in comparison_limits
    }
    validity_checks = {
        "common_reference_valid": reference.public_summary["accepted"],
        **{f"{name}_tangent_qr_valid": run["accepted"] for name, run in runs.items()},
    }
    validity_accepted = all(validity_checks.values())
    classification = classify_isolation(
        validity_accepted=validity_accepted,
        comparisons=comparisons,
    )
    if classification == "reference_shadow_divergence_primary_observed_source":
        status = "accepted_reference_shadow_divergence_primary_observed_source"
        accepted = True
        strongest_claim = (
            "Experiment 007's material policy separation largely collapses when "
            "the tangent and QR variants share one independently validated reference "
            "history; divergence of the independently integrated numerical reference "
            "shadows is therefore the primary observed source of that separation."
        )
        next_question = (
            "Do substantially longer independently integrated Euler-Lagrange QR "
            "runs yield cumulative spectra that statistically reconcile after their "
            "reference shadows decorrelate?"
        )
    elif classification == "material_tangent_or_qr_policy_dependence_remains":
        status = "accepted_material_tangent_or_qr_policy_dependence_remains"
        accepted = True
        strongest_claim = (
            "At least one tangent or QR policy retains a material fraction of "
            "Experiment 007's separation even when all variants share the same "
            "validated reference history."
        )
        next_question = (
            "Which retained tangent-integration or QR-cadence mechanism causes the "
            "material common-reference discrepancy?"
        )
    else:
        status = "unresolved_common_reference_isolation"
        accepted = False
        strongest_claim = (
            "The common-reference diagnostic does not yet isolate reference-shadow "
            "divergence from tangent/QR-policy sensitivity under its declared controls."
        )
        next_question = (
            "Can one narrower refinement of the common-reference construction resolve "
            "the isolation without extending asymptotic duration?"
        )

    public_reference = {
        key: value
        for key, value in reference.public_summary.items()
        if key != "segments"
    }
    summary = {
        "experiment": EXPERIMENT_NAME,
        "status": status,
        "classification": classification,
        "accepted": accepted,
        "question": (
            "Is Experiment 007's material long-time refinement separation primarily "
            "caused by numerical reference-shadow divergence, or does tangent/QR "
            "policy sensitivity remain on one common reference history?"
        ),
        "isolation_strategy": {
            "reference_role": "one immutable piecewise-dense driver shared by all tangent runs",
            "reference_segment_seconds": REFERENCE_SEGMENT_SECONDS,
            "reference_policy": experiment006.policy_dict(COMMON_REFERENCE_POLICY),
            "reference_max_step_seconds": COMMON_REFERENCE_MAX_STEP,
            "local_validation_policy": experiment006.policy_dict(
                REFERENCE_VALIDATION_POLICY
            ),
            "local_validation_max_step_seconds": REFERENCE_VALIDATION_MAX_STEP,
            "reference_rebase": "angles canonicalized to (-pi, pi] between fixed reference segments",
            "tangent_evolution": "dot(Y)=J(x_common(t))Y in physical coordinates",
            "qr_geometry": "Experiment 007 Candidate-A-scaled QR",
            "assumption": (
                "the diagnosis is conditional on the declared common numerical "
                "reference history and its locally validated dense interpolant"
            ),
        },
        "criteria": {
            "reference_local_candidate_a_error": REFERENCE_LOCAL_ERROR_LIMIT,
            "reference_energy_drift": REFERENCE_ENERGY_DRIFT_LIMIT,
            "strict_tangent_difference_per_second": STRICT_DIFFERENCE_LIMIT,
            "half_tangent_step_difference_per_second": HALF_STEP_DIFFERENCE_LIMIT,
            "qr_interval_difference_per_second": QR_INTERVAL_DIFFERENCE_LIMIT,
            "collapse_ratio": COLLAPSE_RATIO_LIMIT,
            "material_remainder_ratio": MATERIAL_REMAINDER_RATIO,
            "late_window_seconds": [LATE_WINDOW_START_SECONDS, duration],
            "criteria_provenance": "predeclared in README before the full run",
        },
        "common_reference": public_reference,
        "tangent_qr_runs": {
            name: public_run_summary(run) for name, run in runs.items()
        },
        "comparisons": comparisons,
        "validity_checks": validity_checks,
        "validity_accepted": validity_accepted,
        "strongest_claim": strongest_claim,
        "claim_boundary": (
            "This diagnostic identifies an observed source of Experiment 007 policy "
            "separation conditional on one common numerical reference history. It "
            "does not establish a converged spectrum, reference-history independence, "
            "a maximal Lyapunov exponent, or chaos classification."
        ),
        "next_question": next_question,
    }
    return {
        "summary": summary,
        "reference": reference,
        "runs": runs,
        "comparisons": comparisons,
    }


def json_write(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def write_reference_timeseries(path: Path, reference: CommonReferenceHistory) -> None:
    fields = ["time_seconds", *experiment007.STATE_ORDER, "normalized_energy_drift"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for time_value, state, energy_drift in zip(
            reference.sample_time,
            reference.sample_state,
            reference.sample_energy_drift,
        ):
            row = {
                "time_seconds": time_value,
                "normalized_energy_drift": energy_drift,
            }
            row.update(dict(zip(experiment007.STATE_ORDER, state)))
            writer.writerow(row)


def write_run_matrix(path: Path, result: dict[str, Any]) -> None:
    fields = [
        "case",
        "rtol",
        "atol",
        "max_step_seconds",
        "qr_interval_seconds",
        *[f"lambda_{index}_per_s" for index in range(1, 5)],
        "final_maximum_difference_per_s",
        "late_window_maximum_difference_per_s",
        "final_separation_ratio",
        "late_window_separation_ratio",
        "accepted_for_collapse",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for name, run in result["runs"].items():
            comparison = result["comparisons"].get(name)
            row: dict[str, Any] = {
                "case": name,
                "rtol": run["solver_policy"]["rtol"],
                "atol": run["solver_policy"]["atol"],
                "max_step_seconds": run["max_step_seconds"],
                "qr_interval_seconds": run["qr_interval_seconds"],
            }
            for index, value in enumerate(
                run["final_diagnostic_spectrum_per_second"], start=1
            ):
                row[f"lambda_{index}_per_s"] = value
            if comparison is None:
                row.update(
                    {
                        "final_maximum_difference_per_s": 0.0,
                        "late_window_maximum_difference_per_s": 0.0,
                        "final_separation_ratio": 0.0,
                        "late_window_separation_ratio": 0.0,
                        "accepted_for_collapse": True,
                    }
                )
            else:
                row.update(
                    {
                        "final_maximum_difference_per_s": comparison[
                            "final_maximum_difference_per_second"
                        ],
                        "late_window_maximum_difference_per_s": comparison[
                            "late_window_maximum_difference_per_second"
                        ],
                        "final_separation_ratio": comparison[
                            "final_separation_ratio"
                        ],
                        "late_window_separation_ratio": comparison[
                            "late_window_separation_ratio"
                        ],
                        "accepted_for_collapse": comparison[
                            "accepted_for_collapse"
                        ],
                    }
                )
            writer.writerow(row)


def write_cumulative_timeseries(path: Path, result: dict[str, Any]) -> None:
    fields = [
        "case",
        "time_seconds",
        *[f"lambda_{index}_per_s" for index in range(1, 5)],
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for name, run in result["runs"].items():
            for cycle in run["cycles"]:
                row: dict[str, Any] = {
                    "case": name,
                    "time_seconds": cycle["end_time_seconds"],
                }
                for index, value in enumerate(
                    cycle["cumulative_finite_time_spectrum_per_second"], start=1
                ):
                    row[f"lambda_{index}_per_s"] = value
                writer.writerow(row)


def load_pyplot():
    import matplotlib.pyplot as plt

    return plt


def save_figure(fig: Any, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    load_pyplot().close(fig)


def write_plots(output_dir: Path, result: dict[str, Any]) -> list[Path]:
    plt = load_pyplot()
    paths: list[Path] = []

    path = output_dir / "01_common_reference_policy_differences.png"
    fig, axes = plt.subplots(2, 2, figsize=(10, 8), sharex=True)
    baseline = result["runs"]["baseline"]
    for name, run in result["runs"].items():
        if name == "baseline":
            continue
        matched_times = common_comparison_times(run["duration_seconds"])
        differences = []
        for time_value in matched_times:
            baseline_value = experiment007.spectrum_at_time(baseline, float(time_value))
            comparison_value = experiment007.spectrum_at_time(run, float(time_value))
            differences.append(np.abs(comparison_value - baseline_value))
        difference_array = np.asarray(differences)
        for component, axis in enumerate(axes.flat):
            axis.plot(
                matched_times,
                difference_array[:, component],
                label=name.replace("_", " "),
            )
            axis.set_title(f"fixed QR column {component + 1}")
            axis.grid(True, alpha=0.25)
    for axis in axes[-1]:
        axis.set_xlabel("time / s")
    for axis in axes[:, 0]:
        axis.set_ylabel("absolute difference / s$^{-1}$")
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Common-reference cumulative QR-policy differences, 60–80 s")
    save_figure(fig, path)
    paths.append(path)

    path = output_dir / "02_reference_local_validation.png"
    fig, axes = plt.subplots(2, 1, figsize=(8, 7), sharex=True)
    segments = result["reference"].public_summary["segments"]
    end_times = [segment["end_time_seconds"] for segment in segments]
    axes[0].semilogy(
        end_times,
        [segment["local_midpoint_candidate_a_error"] for segment in segments],
        label="midpoint",
    )
    axes[0].semilogy(
        end_times,
        [segment["local_endpoint_candidate_a_error"] for segment in segments],
        label="endpoint",
    )
    axes[0].axhline(REFERENCE_LOCAL_ERROR_LIMIT, color="red", linestyle="--")
    axes[0].set(ylabel="Candidate-A error", title="Local dense-reference refinement")
    axes[0].legend()
    axes[1].semilogy(
        result["reference"].sample_time,
        np.maximum(result["reference"].sample_energy_drift, 1.0e-18),
    )
    axes[1].axhline(REFERENCE_ENERGY_DRIFT_LIMIT, color="red", linestyle="--")
    axes[1].set(
        xlabel="time / s",
        ylabel="normalized drift",
        title="Shared reference energy validity",
    )
    for axis in axes:
        axis.grid(True, which="both", alpha=0.25)
    save_figure(fig, path)
    paths.append(path)
    return paths


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_output_bundle(
    result: dict[str, Any], output_dir: Path, *, plots: bool = True
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.json"
    reference_validation_path = output_dir / "reference_validation.json"
    reference_timeseries_path = output_dir / "reference_timeseries.csv"
    run_matrix_path = output_dir / "comparison_matrix.csv"
    cumulative_path = output_dir / "cumulative_timeseries.csv"
    baseline_cycles_path = output_dir / "baseline_cycles.json"
    json_write(summary_path, result["summary"])
    json_write(reference_validation_path, result["reference"].public_summary)
    write_reference_timeseries(reference_timeseries_path, result["reference"])
    write_run_matrix(run_matrix_path, result)
    write_cumulative_timeseries(cumulative_path, result)
    json_write(
        baseline_cycles_path,
        {
            "experiment": EXPERIMENT_NAME,
            "run_id": "baseline",
            "cycles": result["runs"]["baseline"]["cycles"],
        },
    )
    paths = [
        summary_path,
        reference_validation_path,
        reference_timeseries_path,
        run_matrix_path,
        cumulative_path,
        baseline_cycles_path,
    ]
    if plots:
        paths.extend(write_plots(output_dir, result))
    manifest_path = output_dir / "manifest.json"
    manifest = {
        "experiment": EXPERIMENT_NAME,
        "output_role": "Experiment 008 common-reference isolation evidence",
        "claim_boundary": "diagnostic source isolation, not a converged spectrum",
        "source": str(Path(__file__).relative_to(REPOSITORY_ROOT)),
        "files": [
            {
                "path": path.name,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in paths
        ],
    }
    json_write(manifest_path, manifest)
    paths.append(manifest_path)
    return paths


def assert_self_check(result: dict[str, Any]) -> None:
    reference = result["reference"]
    summary = result["summary"]
    assert summary["validity_accepted"] == all(summary["validity_checks"].values())
    assert len(reference.segments) == int(
        round(reference.duration / REFERENCE_SEGMENT_SECONDS)
    )
    np.testing.assert_allclose(
        reference.evaluate(0.0),
        experiment006.canonicalize_state_angles(experiment006.BASE_STATE_RADIANS),
        rtol=0.0,
        atol=1.0e-14,
    )
    for run in result["runs"].values():
        cycle_logs = np.asarray([cycle["cycle_log_growth"] for cycle in run["cycles"]])
        cumulative = np.cumsum(cycle_logs, axis=0)
        np.testing.assert_allclose(
            cumulative,
            run["_cumulative_logs"],
            rtol=0.0,
            atol=experiment007.BOOKKEEPING_ERROR_LIMIT,
        )
    recomputed = classify_isolation(
        validity_accepted=summary["validity_accepted"],
        comparisons=result["comparisons"],
    )
    assert recomputed == summary["classification"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            REPOSITORY_ROOT
            / "development/chaos_content/experiments/outputs/008/baseline"
        ),
    )
    parser.add_argument("--no-plots", action="store_true")
    parser.add_argument("--self-check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_investigation()
    if args.self_check:
        assert_self_check(result)
    paths = write_output_bundle(result, args.output_dir, plots=not args.no_plots)
    summary = result["summary"]
    print(
        json.dumps(
            {
                "status": summary["status"],
                "classification": summary["classification"],
                "accepted": summary["accepted"],
                "baseline_diagnostic_spectrum_per_second": summary[
                    "tangent_qr_runs"
                ]["baseline"]["final_diagnostic_spectrum_per_second"],
                "maximum_local_reference_error": summary["common_reference"][
                    "maximum_local_candidate_a_error"
                ],
                "output_dir": str(args.output_dir),
                "files_written": len(paths),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
