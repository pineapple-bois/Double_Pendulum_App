"""Focused audit of Experiment 017's bounded Fortran max-step errors."""

from __future__ import annotations

import argparse
import json
import math
import sys
import warnings
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Callable

import numpy as np
from scipy.integrate import ode, solve_ivp


REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from development.chaos_content.prototypes.state_space_maps.src.lyapunov.compiled import (
    compiled_rhs,
    run_renormalized_tangent_compiled,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.compiled_dop853 import (
    COMPILED_DOP853_EVALUATOR,
    evaluate_renormalized_tangent_compiled_dop853,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.reference import (
    CandidateAMetric,
    RenormalizedTangentResult,
    RenormalizedTangentSpec,
    SolverSpec,
    _energy_scale,
    _run_renormalized_tangent_with_rhs,
    run_renormalized_tangent,
    simple_energy,
)


DEFAULT_OUTPUT_PATH = (
    Path(__file__).resolve().parents[3]
    / "outputs"
    / "rectangular_work_unit_boundary"
    / "max_step_audit.json"
)
TIME_ABSOLUTE_TOLERANCE = 1.0e-13
MAX_STEP_FLOATING_POINT_ALLOWANCE = 64.0 * np.finfo(float).eps
MAX_INTERNAL_STEPS = 100_000

RATE_ABSOLUTE_TOLERANCE = 1.0e-8
CYCLE_LOG_ABSOLUTE_TOLERANCE = 5.0e-8
FINAL_REFERENCE_DISTANCE_TOLERANCE = 1.0e-7
FINAL_TANGENT_DISTANCE_TOLERANCE = 1.0e-7
ENERGY_DIAGNOSTIC_ABSOLUTE_TOLERANCE = 1.0e-8


@dataclass(frozen=True)
class AuditCase:
    name: str
    source_grid: str
    theta1_index: int
    theta2_index: int
    theta1_degrees: float
    theta2_degrees: float
    expected_promoted_status: str
    relationship: str


AUDIT_CASES = (
    AuditCase(
        name="17x17_failure",
        source_grid="17x17",
        theta1_index=7,
        theta2_index=1,
        theta1_degrees=177.75,
        theta2_degrees=170.25,
        expected_promoted_status="execution_error",
        relationship="known Experiment 017 failure",
    ),
    AuditCase(
        name="17x17_left_neighbor",
        source_grid="17x17",
        theta1_index=6,
        theta2_index=1,
        theta1_degrees=176.5,
        theta2_degrees=170.25,
        expected_promoted_status="completed_valid",
        relationship="immediate theta1-axis neighbor of 17x17_failure",
    ),
    AuditCase(
        name="25x25_failure",
        source_grid="25x25",
        theta1_index=15,
        theta2_index=2,
        theta1_degrees=181.5,
        theta2_degrees=170.66666666666666,
        expected_promoted_status="execution_error",
        relationship="known Experiment 017 failure unique to the 25x25 axis",
    ),
    AuditCase(
        name="25x25_left_neighbor",
        source_grid="25x25",
        theta1_index=14,
        theta2_index=2,
        theta1_degrees=180.66666666666666,
        theta2_degrees=170.66666666666666,
        expected_promoted_status="completed_valid",
        relationship="immediate theta1-axis neighbor of 25x25_failure",
    ),
)


@dataclass(frozen=True)
class SegmentTrace:
    segment_number: int
    start_time: float
    end_time: float
    requested_max_step: float
    configured_fortran_max_step: float | None
    accepted_time: tuple[float, ...]
    accepted_step_count: int
    reported_fortran_step_count: int | None
    reported_fortran_accepted_step_count: int | None
    reported_fortran_rejected_step_count: int | None
    maximum_step_gap: float
    maximum_gap_start: float
    maximum_gap_end: float
    maximum_gap_is_endpoint_step: bool
    maximum_gap_exceeds_declared_limit: bool
    endpoint_reached: bool
    successful: bool
    return_code: int | None
    function_evaluations: int
    all_states_finite: bool
    stretch_factor: float
    log_stretch_increment: float
    post_reset_norm_error: float
    maximum_normalized_energy_drift: float
    warning_messages: tuple[str, ...]
    initial_state: tuple[float, ...]
    final_state: tuple[float, ...]


class TracedFortranDop853Solver:
    """Observe all successful Fortran steps without applying the wrapper check."""

    def __init__(
        self,
        spec: RenormalizedTangentSpec,
        *,
        internal_max_step_factor: float = 1.0,
    ) -> None:
        self.spec = spec
        self.internal_max_step_factor = internal_max_step_factor
        self.metric = CandidateAMetric(
            spec.characteristic_length,
            spec.parameters.gravity,
        )
        self.initial_energy = float(simple_energy(spec.initial_state.as_array(), spec.parameters))
        self.traces: list[SegmentTrace] = []

    def __call__(
        self,
        rhs: Callable[[float, np.ndarray], np.ndarray],
        initial: np.ndarray,
        requested: np.ndarray,
        solver: SolverSpec,
        max_step: float,
    ) -> tuple[np.ndarray, int]:
        if solver.method.upper() != "DOP853":
            raise ValueError("The audit supports only DOP853.")
        initial = np.asarray(initial, dtype=float)
        requested = np.asarray(requested, dtype=float)
        start = float(requested[0])
        end = float(requested[-1])
        accepted_times: list[float] = []
        accepted_states: list[np.ndarray] = []
        function_evaluations = 0
        internal_max_step = float(
            np.nextafter(max_step * self.internal_max_step_factor, 0.0)
            if self.internal_max_step_factor < 1.0
            else max_step
        )

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
            max_step=internal_max_step,
            nsteps=MAX_INTERNAL_STEPS,
            verbosity=-1,
        )
        integrator.set_solout(observe)
        integrator.set_initial_value(initial, start)
        configured_max_step = float(integrator._integrator.work[5])
        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter("always")
            final_state = np.asarray(integrator.integrate(end), dtype=float)
        return_code = integrator.get_return_code()
        successful = bool(integrator.successful() and return_code == 1)
        endpoint_reached = math.isclose(
            float(integrator.t),
            end,
            rel_tol=0.0,
            abs_tol=TIME_ABSOLUTE_TOLERANCE,
        )
        if not successful:
            raise RuntimeError(
                f"Diagnostic Fortran integration failed with return code {return_code}."
            )
        if not endpoint_reached:
            raise RuntimeError("Diagnostic Fortran integration missed its endpoint.")

        time = np.asarray(accepted_times, dtype=float)
        state = np.asarray(accepted_states, dtype=float)
        if time[0] != start or time[-1] != end:
            raise RuntimeError("Diagnostic callback did not observe both segment boundaries.")
        gaps = np.diff(time)
        maximum_gap_index = int(np.argmax(gaps))
        maximum_gap = float(gaps[maximum_gap_index])
        allowed = max_step + MAX_STEP_FLOATING_POINT_ALLOWANCE * max(
            1.0,
            abs(max_step),
        )
        final_augmented = state[-1]
        scaled_tangent = self.metric.scale_tangent(final_augmented[4:])
        stretch_factor = float(np.linalg.norm(scaled_tangent))
        reset_tangent = np.linalg.solve(
            self.metric.scaling_matrix(),
            scaled_tangent / stretch_factor,
        )
        energy = simple_energy(state[:, :4], self.spec.parameters)
        energy_drift = float(
            np.max(
                np.abs(energy - self.initial_energy)
                / _energy_scale(self.spec.parameters)
            )
        )
        iwork = np.asarray(integrator._integrator.iwork, dtype=int)
        self.traces.append(
            SegmentTrace(
                segment_number=len(self.traces) + 1,
                start_time=start,
                end_time=end,
                requested_max_step=max_step,
                configured_fortran_max_step=configured_max_step,
                accepted_time=tuple(float(value) for value in time),
                accepted_step_count=len(time) - 1,
                reported_fortran_step_count=int(iwork[17]),
                reported_fortran_accepted_step_count=int(iwork[18]),
                reported_fortran_rejected_step_count=int(iwork[19]),
                maximum_step_gap=maximum_gap,
                maximum_gap_start=float(time[maximum_gap_index]),
                maximum_gap_end=float(time[maximum_gap_index + 1]),
                maximum_gap_is_endpoint_step=maximum_gap_index == len(gaps) - 1,
                maximum_gap_exceeds_declared_limit=bool(maximum_gap > allowed),
                endpoint_reached=endpoint_reached,
                successful=successful,
                return_code=return_code,
                function_evaluations=function_evaluations,
                all_states_finite=bool(np.all(np.isfinite(state))),
                stretch_factor=stretch_factor,
                log_stretch_increment=math.log(stretch_factor),
                post_reset_norm_error=abs(
                    float(self.metric.tangent_norm(reset_tangent)) - 1.0
                ),
                maximum_normalized_energy_drift=energy_drift,
                warning_messages=tuple(str(item.message) for item in caught_warnings),
                initial_state=tuple(float(value) for value in initial),
                final_state=tuple(float(value) for value in final_state),
            )
        )
        return state, function_evaluations


class TracedSolveIvpDop853Solver:
    """Observe solve_ivp's internal accepted-step sequence with unchanged policy."""

    def __init__(self, spec: RenormalizedTangentSpec) -> None:
        self.spec = spec
        self.metric = CandidateAMetric(
            spec.characteristic_length,
            spec.parameters.gravity,
        )
        self.initial_energy = float(simple_energy(spec.initial_state.as_array(), spec.parameters))
        self.traces: list[SegmentTrace] = []

    def __call__(
        self,
        rhs: Callable[[float, np.ndarray], np.ndarray],
        initial: np.ndarray,
        requested: np.ndarray,
        solver: SolverSpec,
        max_step: float,
    ) -> tuple[np.ndarray, int]:
        start = float(requested[0])
        end = float(requested[-1])
        result = solve_ivp(
            rhs,
            (start, end),
            np.asarray(initial, dtype=float),
            method=solver.method,
            rtol=solver.rtol,
            atol=solver.atol,
            max_step=max_step,
        )
        state = np.asarray(result.y.T, dtype=float)
        time = np.asarray(result.t, dtype=float)
        if not result.success:
            raise RuntimeError(f"Diagnostic solve_ivp integration failed: {result.message}")
        gaps = np.diff(time)
        maximum_gap_index = int(np.argmax(gaps))
        maximum_gap = float(gaps[maximum_gap_index])
        allowed = max_step + MAX_STEP_FLOATING_POINT_ALLOWANCE * max(
            1.0,
            abs(max_step),
        )
        final_augmented = state[-1]
        scaled_tangent = self.metric.scale_tangent(final_augmented[4:])
        stretch_factor = float(np.linalg.norm(scaled_tangent))
        reset_tangent = np.linalg.solve(
            self.metric.scaling_matrix(),
            scaled_tangent / stretch_factor,
        )
        energy = simple_energy(state[:, :4], self.spec.parameters)
        energy_drift = float(
            np.max(
                np.abs(energy - self.initial_energy)
                / _energy_scale(self.spec.parameters)
            )
        )
        self.traces.append(
            SegmentTrace(
                segment_number=len(self.traces) + 1,
                start_time=start,
                end_time=end,
                requested_max_step=max_step,
                configured_fortran_max_step=None,
                accepted_time=tuple(float(value) for value in time),
                accepted_step_count=len(time) - 1,
                reported_fortran_step_count=None,
                reported_fortran_accepted_step_count=None,
                reported_fortran_rejected_step_count=None,
                maximum_step_gap=maximum_gap,
                maximum_gap_start=float(time[maximum_gap_index]),
                maximum_gap_end=float(time[maximum_gap_index + 1]),
                maximum_gap_is_endpoint_step=maximum_gap_index == len(gaps) - 1,
                maximum_gap_exceeds_declared_limit=bool(maximum_gap > allowed),
                endpoint_reached=math.isclose(
                    float(time[-1]),
                    end,
                    rel_tol=0.0,
                    abs_tol=TIME_ABSOLUTE_TOLERANCE,
                ),
                successful=True,
                return_code=0,
                function_evaluations=int(result.nfev),
                all_states_finite=bool(np.all(np.isfinite(state))),
                stretch_factor=stretch_factor,
                log_stretch_increment=math.log(stretch_factor),
                post_reset_norm_error=abs(
                    float(self.metric.tangent_norm(reset_tangent)) - 1.0
                ),
                maximum_normalized_energy_drift=energy_drift,
                warning_messages=(),
                initial_state=tuple(float(value) for value in initial),
                final_state=tuple(float(value) for value in state[-1]),
            )
        )
        return state, int(result.nfev)


def _spec_for_case(case: AuditCase) -> RenormalizedTangentSpec:
    base = RenormalizedTangentSpec()
    return replace(
        base,
        initial_state=replace(
            base.initial_state,
            theta1=math.radians(case.theta1_degrees),
            theta2=math.radians(case.theta2_degrees),
        ),
    )


def _compare_results(
    oracle: RenormalizedTangentResult,
    candidate: RenormalizedTangentResult,
) -> dict[str, object]:
    metric = oracle.metric
    rate_error = abs(
        oracle.finite_time_stretching_rate
        - candidate.finite_time_stretching_rate
    )
    cycle_log_error = float(
        np.max(
            np.abs(
                oracle.log_stretch_increment - candidate.log_stretch_increment
            )
        )
    )
    reference_distance = float(
        metric.distance(
            oracle.final_reference_state,
            candidate.final_reference_state,
        )
    )
    tangent_distance = float(
        metric.tangent_norm(
            candidate.final_unit_tangent - oracle.final_unit_tangent
        )
    )
    energy_error = abs(
        oracle.diagnostics.maximum_normalized_reference_energy_drift
        - candidate.diagnostics.maximum_normalized_reference_energy_drift
    )
    accepted = bool(
        rate_error <= RATE_ABSOLUTE_TOLERANCE
        and cycle_log_error <= CYCLE_LOG_ABSOLUTE_TOLERANCE
        and reference_distance <= FINAL_REFERENCE_DISTANCE_TOLERANCE
        and tangent_distance <= FINAL_TANGENT_DISTANCE_TOLERANCE
        and energy_error <= ENERGY_DIAGNOSTIC_ABSOLUTE_TOLERANCE
        and oracle.diagnostics.numerically_valid
        == candidate.diagnostics.numerically_valid
        and oracle.diagnostics.validity_issues
        == candidate.diagnostics.validity_issues
    )
    return {
        "accepted": accepted,
        "absolute_rate_error_per_second": rate_error,
        "maximum_cycle_log_absolute_error": cycle_log_error,
        "final_reference_candidate_a_distance": reference_distance,
        "final_tangent_candidate_a_distance": tangent_distance,
        "energy_diagnostic_absolute_error": energy_error,
        "oracle_numerically_valid": oracle.diagnostics.numerically_valid,
        "candidate_numerically_valid": candidate.diagnostics.numerically_valid,
        "validity_issues_equal": (
            oracle.diagnostics.validity_issues
            == candidate.diagnostics.validity_issues
        ),
    }


def _no_solout_replay(
    trace: SegmentTrace,
    spec: RenormalizedTangentSpec,
) -> dict[str, object]:
    function_evaluations = 0
    rhs = compiled_rhs(spec.parameters)

    def counted_rhs(time_value: float, state: np.ndarray) -> np.ndarray:
        nonlocal function_evaluations
        function_evaluations += 1
        return rhs(time_value, state)

    integrator = ode(counted_rhs).set_integrator(
        "dop853",
        rtol=spec.solver.rtol,
        atol=spec.solver.atol,
        max_step=trace.requested_max_step,
        nsteps=MAX_INTERNAL_STEPS,
        verbosity=-1,
    )
    integrator.set_initial_value(np.asarray(trace.initial_state), trace.start_time)
    final_state = np.asarray(integrator.integrate(trace.end_time), dtype=float)
    iwork = np.asarray(integrator._integrator.iwork, dtype=int)
    return {
        "successful": bool(integrator.successful()),
        "return_code": integrator.get_return_code(),
        "endpoint_reached": math.isclose(
            float(integrator.t),
            trace.end_time,
            rel_tol=0.0,
            abs_tol=TIME_ABSOLUTE_TOLERANCE,
        ),
        "function_evaluations": function_evaluations,
        "reported_fortran_step_count": int(iwork[17]),
        "reported_fortran_accepted_step_count": int(iwork[18]),
        "reported_fortran_rejected_step_count": int(iwork[19]),
        "maximum_final_state_absolute_difference_from_solout_run": float(
            np.max(np.abs(final_state - np.asarray(trace.final_state)))
        ),
        "all_states_finite": bool(np.all(np.isfinite(final_state))),
    }


def _audit_case(case: AuditCase) -> dict[str, object]:
    spec = _spec_for_case(case)
    promoted = evaluate_renormalized_tangent_compiled_dop853(spec)
    compiled_oracle = run_renormalized_tangent_compiled(spec)
    mathematical_oracle = run_renormalized_tangent(spec)

    fortran_solver = TracedFortranDop853Solver(spec)
    unchecked_fortran = _run_renormalized_tangent_with_rhs(
        spec,
        compiled_rhs(spec.parameters),
        segment_solver=fortran_solver,
    )
    solve_ivp_solver = TracedSolveIvpDop853Solver(spec)
    traced_solve_ivp = _run_renormalized_tangent_with_rhs(
        spec,
        compiled_rhs(spec.parameters),
        segment_solver=solve_ivp_solver,
    )
    compensated_solver = TracedFortranDop853Solver(
        spec,
        internal_max_step_factor=1.0 / 1.01,
    )
    compensated_fortran = _run_renormalized_tangent_with_rhs(
        spec,
        compiled_rhs(spec.parameters),
        segment_solver=compensated_solver,
    )

    violating_fortran = [
        trace for trace in fortran_solver.traces
        if trace.maximum_gap_exceeds_declared_limit
    ]
    violating_solve_ivp = [
        trace for trace in solve_ivp_solver.traces
        if trace.maximum_gap_exceeds_declared_limit
    ]
    replays = [
        {
            "segment_number": trace.segment_number,
            **_no_solout_replay(trace, spec),
        }
        for trace in violating_fortran
    ]
    status_matches_selection = promoted.status.value == case.expected_promoted_status
    return {
        "case": asdict(case),
        "promoted_evaluation": {
            "evaluator": promoted.evaluator,
            "status": promoted.status.value,
            "value": promoted.value,
            "error_type": promoted.error_type,
            "error_message": promoted.error_message,
            "status_matches_selection": status_matches_selection,
        },
        "resolved_contract": {
            "duration_seconds": spec.duration,
            "renormalization_interval_seconds": spec.renormalization_interval,
            "sampling_interval_seconds": spec.sampling_interval,
            "requested_max_step_seconds": (
                unchecked_fortran.diagnostics.max_step_seconds
            ),
            "solver_method": spec.solver.method,
            "rtol": spec.solver.rtol,
            "atol": spec.solver.atol,
            "energy_drift_limit": spec.energy_drift_limit,
            "reset_norm_tolerance": spec.renormalization_norm_tolerance,
        },
        "fortran_unchecked": {
            "completed": True,
            "finite_time_rate": unchecked_fortran.finite_time_stretching_rate,
            "numerically_valid": unchecked_fortran.diagnostics.numerically_valid,
            "validity_issues": unchecked_fortran.diagnostics.validity_issues,
            "maximum_energy_drift": (
                unchecked_fortran.diagnostics.maximum_normalized_reference_energy_drift
            ),
            "maximum_post_reset_norm_error": (
                unchecked_fortran.diagnostics.maximum_post_renormalization_norm_error
            ),
            "function_evaluations": (
                unchecked_fortran.diagnostics.solver_function_evaluations
            ),
            "violating_segment_numbers": [
                trace.segment_number for trace in violating_fortran
            ],
            "segments": [asdict(trace) for trace in fortran_solver.traces],
            "comparison_to_compiled_solve_ivp_oracle": _compare_results(
                compiled_oracle,
                unchecked_fortran,
            ),
        },
        "compiled_solve_ivp_oracle": {
            "completed": True,
            "finite_time_rate": compiled_oracle.finite_time_stretching_rate,
            "numerically_valid": compiled_oracle.diagnostics.numerically_valid,
            "validity_issues": compiled_oracle.diagnostics.validity_issues,
            "maximum_energy_drift": (
                compiled_oracle.diagnostics.maximum_normalized_reference_energy_drift
            ),
            "maximum_post_reset_norm_error": (
                compiled_oracle.diagnostics.maximum_post_renormalization_norm_error
            ),
            "function_evaluations": compiled_oracle.diagnostics.solver_function_evaluations,
            "traced_internal_steps": {
                "completed": True,
                "violating_segment_numbers": [
                    trace.segment_number for trace in violating_solve_ivp
                ],
                "segments": [asdict(trace) for trace in solve_ivp_solver.traces],
                "comparison_to_uniform_grid_oracle": _compare_results(
                    compiled_oracle,
                    traced_solve_ivp,
                ),
            },
        },
        "conservative_fortran_probe": {
            "diagnostic_only": True,
            "internal_max_step_factor": 1.0 / 1.01,
            "completed": True,
            "finite_time_rate": compensated_fortran.finite_time_stretching_rate,
            "numerically_valid": compensated_fortran.diagnostics.numerically_valid,
            "violating_segment_numbers": [
                trace.segment_number
                for trace in compensated_solver.traces
                if trace.maximum_gap_exceeds_declared_limit
            ],
            "maximum_accepted_step_gap": max(
                trace.maximum_step_gap for trace in compensated_solver.traces
            ),
            "maximum_configured_fortran_step": max(
                trace.configured_fortran_max_step
                for trace in compensated_solver.traces
                if trace.configured_fortran_max_step is not None
            ),
            "comparison_to_compiled_solve_ivp_oracle": _compare_results(
                compiled_oracle,
                compensated_fortran,
            ),
        },
        "mathematical_solve_ivp_oracle": {
            "completed": True,
            "finite_time_rate": mathematical_oracle.finite_time_stretching_rate,
            "numerically_valid": mathematical_oracle.diagnostics.numerically_valid,
            "validity_issues": mathematical_oracle.diagnostics.validity_issues,
            "maximum_energy_drift": (
                mathematical_oracle.diagnostics.maximum_normalized_reference_energy_drift
            ),
            "maximum_post_reset_norm_error": (
                mathematical_oracle.diagnostics.maximum_post_renormalization_norm_error
            ),
            "function_evaluations": mathematical_oracle.diagnostics.solver_function_evaluations,
            "comparison_to_compiled_solve_ivp_oracle": _compare_results(
                compiled_oracle,
                mathematical_oracle,
            ),
        },
        "no_solout_replays": replays,
        "case_checks_passed": bool(
            status_matches_selection
            and compiled_oracle.diagnostics.numerically_valid
            and mathematical_oracle.diagnostics.numerically_valid
            and traced_solve_ivp.diagnostics.numerically_valid
            and not violating_solve_ivp
            and _compare_results(compiled_oracle, mathematical_oracle)["accepted"]
            and _compare_results(compiled_oracle, traced_solve_ivp)["accepted"]
            and _compare_results(compiled_oracle, unchecked_fortran)["accepted"]
            and _compare_results(compiled_oracle, compensated_fortran)["accepted"]
            and not any(
                trace.maximum_gap_exceeds_declared_limit
                for trace in compensated_solver.traces
            )
            and all(
                trace.accepted_step_count
                == trace.reported_fortran_accepted_step_count
                for trace in fortran_solver.traces
            )
            and all(replay["successful"] for replay in replays)
        ),
    }


def run_audit() -> dict[str, object]:
    assessments = [_audit_case(case) for case in AUDIT_CASES]
    failing = [
        item for item in assessments
        if item["promoted_evaluation"]["status"] == "execution_error"
    ]
    neighboring = [
        item for item in assessments
        if item["promoted_evaluation"]["status"] == "completed_valid"
    ]
    all_failing_violations_are_endpoint_steps = all(
        trace["maximum_gap_is_endpoint_step"]
        for item in failing
        for trace in item["fortran_unchecked"]["segments"]
        if trace["maximum_gap_exceeds_declared_limit"]
    )
    callback_counts_match_fortran = all(
        trace["accepted_step_count"]
        == trace["reported_fortran_accepted_step_count"]
        for item in assessments
        for trace in item["fortran_unchecked"]["segments"]
    )
    no_solout_final_states_match = all(
        replay["maximum_final_state_absolute_difference_from_solout_run"] == 0.0
        for item in failing
        for replay in item["no_solout_replays"]
    )
    conservative_probe_passed = all(
        not item["conservative_fortran_probe"]["violating_segment_numbers"]
        and item["conservative_fortran_probe"][
            "comparison_to_compiled_solve_ivp_oracle"
        ]["accepted"]
        for item in assessments
    )
    return {
        "investigation": "experiment_017_max_step_audit",
        "question": (
            "Why do selected Experiment 017 cells produce promoted Fortran "
            "DOP853 max_step execution errors?"
        ),
        "decision": "A",
        "conclusion": (
            "The legacy Fortran DOP853 solver completes successfully but its "
            "endpoint-snap branch can take a final accepted segment step up to "
            "1.01 times the capped proposal. That step genuinely exceeds the "
            "declared strict max_step in the selected failing cells, so the "
            "promoted wrapper correctly preserves the Experiment 015 contract "
            "by returning an execution error."
        ),
        "mechanism": {
            "requested_max_step_is_passed_to_fortran_work_6": True,
            "solout_is_called_after_each_successful_step": True,
            "fortran_endpoint_rule": (
                "if the endpoint is within 1.01 times the current proposed step, "
                "replace that step by the entire remaining interval"
            ),
            "next_step_hmax_cap_occurs_after_endpoint_acceptance": True,
            "wrapper_check_is_post_integration": True,
            "wrapper_tolerance_seconds": MAX_STEP_FLOATING_POINT_ALLOWANCE,
        },
        "aggregate_checks": {
            "all_case_checks_passed": all(
                item["case_checks_passed"] for item in assessments
            ),
            "selected_failing_case_count": len(failing),
            "selected_neighbor_case_count": len(neighboring),
            "all_failing_violations_are_endpoint_steps": (
                all_failing_violations_are_endpoint_steps
            ),
            "callback_counts_match_fortran_accepted_counts": (
                callback_counts_match_fortran
            ),
            "no_solout_final_states_match_observed_runs_exactly": (
                no_solout_final_states_match
            ),
            "all_solve_ivp_internal_steps_respect_max_step": all(
                not trace["maximum_gap_exceeds_declared_limit"]
                for item in assessments
                for trace in item["compiled_solve_ivp_oracle"][
                    "traced_internal_steps"
                ]["segments"]
            ),
            "conservative_fortran_probe_passed": conservative_probe_passed,
        },
        "cases": assessments,
        "repair": {
            "promoted_wrapper_change_justified": False,
            "reason": (
                "Experiment 015 explicitly required observed accepted-step gaps "
                "to obey max_step within floating-point allowance. Removing or "
                "loosening that check would change the promoted numerical contract."
            ),
            "future_option_requiring_new_evidence": (
                "A diagnostic internal cap of nextafter(declared_max_step / 1.01, "
                "0) prevented the endpoint snap from exceeding the unchanged "
                "external cap on all four selected cases and retained the existing "
                "equivalence gates. Promoting that translation requires renewed "
                "Experiment 015 fixtures and complete 17x17/25x25 regression; the "
                "audit does not implement it."
            ),
        },
        "explicit_nonclaims": [
            "The audit does not show that the underlying solutions are inaccurate.",
            "It does not validate a relaxed max_step policy.",
            "It does not generalize beyond the selected Experiment 017 cells.",
            "It does not modify the promoted evaluator or map pipeline.",
        ],
    }


def save_audit(audit: dict[str, object], path: Path = DEFAULT_OUTPUT_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output:
        json.dump(audit, output, indent=2, allow_nan=False)
        output.write("\n")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    arguments = parser.parse_args()
    audit = run_audit()
    save_audit(audit, arguments.output)
    return 0 if audit["aggregate_checks"]["all_case_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
