"""Experiment 015: test a compiled Fortran DOP853 integration boundary.

The accepted observable remains owned by the Lyapunov prototype.  This module
provides only an experiment-local segment adapter, comparison harness, timing
measurements, and machine-readable evidence.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import sys
import tempfile
import warnings
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Callable

RUNTIME_CACHE_ROOT = Path(tempfile.gettempdir()) / "double-pendulum-chaos-cache"
RUNTIME_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(RUNTIME_CACHE_ROOT / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(RUNTIME_CACHE_ROOT / "xdg"))

import numba
import numpy as np
import scipy
from scipy.integrate import ode


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from development.chaos_content.prototypes.lyapunov_exponents.compiled import (
    compiled_reference_and_tangent_rhs,
    compiled_rhs,
    run_renormalized_tangent_compiled,
)
from development.chaos_content.prototypes.lyapunov_exponents.compiled_equivalence import (
    BENCHMARK_ANGLE_PAIRS_DEGREES,
    CYCLE_LOG_ABSOLUTE_TOLERANCE,
    ENERGY_DIAGNOSTIC_ABSOLUTE_TOLERANCE,
    FINAL_REFERENCE_DISTANCE_TOLERANCE,
    FINAL_TANGENT_DISTANCE_TOLERANCE,
    RATE_ABSOLUTE_TOLERANCE,
    VALIDATION_ANGLE_PAIRS_DEGREES,
    compare_results,
    validation_spec,
)
from development.chaos_content.prototypes.lyapunov_exponents.reference import (
    RenormalizedTangentResult,
    RenormalizedTangentSpec,
    SolverSpec,
    _run_renormalized_tangent_with_rhs,
    _solve_segment,
)


EXPERIMENT_NAME = "compiled_integration_boundary"
DEFAULT_OUTPUT_DIRECTORY = (
    Path(__file__).resolve().parents[2]
    / "outputs"
    / EXPERIMENT_NAME
    / "baseline"
)
DEFAULT_EVIDENCE_PATH = DEFAULT_OUTPUT_DIRECTORY / "summary.json"
MATERIAL_SPEEDUP_GATE = 2.0
TIME_ABSOLUTE_TOLERANCE = 1.0e-13
MAX_STEP_FLOATING_POINT_ALLOWANCE = 64.0 * np.finfo(float).eps
FORTRAN_MAX_INTERNAL_STEPS = 100_000


SegmentSolver = Callable[
    [
        Callable[[float, np.ndarray], np.ndarray],
        np.ndarray,
        np.ndarray,
        SolverSpec,
        float,
    ],
    tuple[np.ndarray, int],
]


@dataclass(frozen=True)
class SegmentObservation:
    """Accepted-step evidence for one Fortran DOP853 segment."""

    start_time: float
    end_time: float
    accepted_time: np.ndarray
    accepted_state: np.ndarray
    function_evaluations: int
    solver_seconds: float
    return_code: int | None
    warning_messages: tuple[str, ...]
    accepted_steps_observed: bool

    @property
    def accepted_step_count(self) -> int:
        return max(0, len(self.accepted_time) - 1)

    @property
    def maximum_step_gap(self) -> float:
        if len(self.accepted_time) < 2:
            return 0.0
        return float(np.max(np.diff(self.accepted_time)))


@dataclass(frozen=True)
class CandidateRun:
    """One candidate observable result plus experiment-only integration data."""

    result: RenormalizedTangentResult
    segments: tuple[SegmentObservation, ...]
    elapsed_seconds: float

    @property
    def segment_solver_seconds(self) -> float:
        return float(sum(segment.solver_seconds for segment in self.segments))

    @property
    def accepted_step_count(self) -> int:
        return sum(segment.accepted_step_count for segment in self.segments)

    @property
    def maximum_accepted_step_gap(self) -> float:
        return max(segment.maximum_step_gap for segment in self.segments)


class FortranDop853SegmentSolver:
    """Integrate one segment once with SciPy's compiled Fortran DOP853."""

    def __init__(self, *, observe_accepted_steps: bool = True) -> None:
        self.observe_accepted_steps = observe_accepted_steps
        self.observations: list[SegmentObservation] = []

    def __call__(
        self,
        rhs: Callable[[float, np.ndarray], np.ndarray],
        initial: np.ndarray,
        requested: np.ndarray,
        solver: SolverSpec,
        max_step: float,
    ) -> tuple[np.ndarray, int]:
        if solver.method.upper() != "DOP853":
            raise ValueError("Experiment 015 supports only the declared DOP853 policy.")

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

        started = perf_counter()
        integrator = ode(counted_rhs).set_integrator(
            "dop853",
            rtol=solver.rtol,
            atol=solver.atol,
            max_step=max_step,
            nsteps=FORTRAN_MAX_INTERNAL_STEPS,
            verbosity=-1,
        )
        if self.observe_accepted_steps:
            integrator.set_solout(observe)
        integrator.set_initial_value(initial, start)
        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter("always")
            final_state = np.asarray(integrator.integrate(end), dtype=float)
        solver_seconds = perf_counter() - started
        return_code = integrator.get_return_code()
        warning_messages = tuple(str(item.message) for item in caught_warnings)

        if not integrator.successful():
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
            float(integrator.t), end, rel_tol=0.0, abs_tol=TIME_ABSOLUTE_TOLERANCE
        ):
            raise RuntimeError(
                "Fortran DOP853 did not reach the requested segment endpoint: "
                f"{integrator.t} != {end}."
            )

        if self.observe_accepted_steps:
            if not accepted_times or not math.isclose(
                accepted_times[0], start, rel_tol=0.0, abs_tol=TIME_ABSOLUTE_TOLERANCE
            ):
                accepted_times.insert(0, start)
                accepted_states.insert(0, initial.copy())
            if not math.isclose(
                accepted_times[-1], end, rel_tol=0.0, abs_tol=TIME_ABSOLUTE_TOLERANCE
            ):
                accepted_times.append(end)
                accepted_states.append(final_state.copy())
        else:
            accepted_times = [start, end]
            accepted_states = [initial.copy(), final_state.copy()]

        time_array = np.asarray(accepted_times, dtype=float)
        state_array = np.asarray(accepted_states, dtype=float)
        if (
            time_array.ndim != 1
            or state_array.shape != (len(time_array), len(initial))
            or not np.all(np.isfinite(time_array))
            or not np.all(np.isfinite(state_array))
            or not np.all(np.diff(time_array) > 0.0)
        ):
            raise RuntimeError("Fortran DOP853 accepted-step output is invalid.")
        maximum_gap = float(np.max(np.diff(time_array)))
        allowed_max_step = max_step + MAX_STEP_FLOATING_POINT_ALLOWANCE * max(
            1.0, abs(max_step)
        )
        if self.observe_accepted_steps and maximum_gap > allowed_max_step:
            raise RuntimeError(
                "Fortran DOP853 exceeded the declared max_step: "
                f"{maximum_gap} > {max_step}."
            )

        observation = SegmentObservation(
            start_time=start,
            end_time=end,
            accepted_time=time_array,
            accepted_state=state_array,
            function_evaluations=function_evaluations,
            solver_seconds=solver_seconds,
            return_code=return_code,
            warning_messages=warning_messages,
            accepted_steps_observed=self.observe_accepted_steps,
        )
        self.observations.append(observation)
        return state_array, function_evaluations


class TimedSegmentSolver:
    """Record segment time without changing another segment solver."""

    def __init__(self, solver: SegmentSolver) -> None:
        self.solver = solver
        self.elapsed_seconds: list[float] = []

    def __call__(
        self,
        rhs: Callable[[float, np.ndarray], np.ndarray],
        initial: np.ndarray,
        requested: np.ndarray,
        solver: SolverSpec,
        max_step: float,
    ) -> tuple[np.ndarray, int]:
        started = perf_counter()
        result = self.solver(rhs, initial, requested, solver, max_step)
        self.elapsed_seconds.append(perf_counter() - started)
        return result


def solve_ivp_endpoint_only_segment(
    rhs: Callable[[float, np.ndarray], np.ndarray],
    initial: np.ndarray,
    requested: np.ndarray,
    solver: SolverSpec,
    max_step: float,
) -> tuple[np.ndarray, int]:
    """Profiling control: retain only segment endpoints from solve_ivp.

    This deliberately changes diagnostic sampling and is not a candidate
    scientific implementation.
    """

    endpoint_times = np.asarray((requested[0], requested[-1]), dtype=float)
    return _solve_segment(rhs, initial, endpoint_times, solver, max_step)


def _run_with_segment_solver(
    spec: RenormalizedTangentSpec,
    segment_solver: SegmentSolver,
) -> RenormalizedTangentResult:
    return _run_renormalized_tangent_with_rhs(
        spec,
        compiled_rhs(spec.parameters),
        segment_solver=segment_solver,
    )


def run_fortran_candidate(
    spec: RenormalizedTangentSpec,
    *,
    observe_accepted_steps: bool = True,
) -> CandidateRun:
    """Evaluate the accepted observable through the experimental boundary."""

    segment_solver = FortranDop853SegmentSolver(
        observe_accepted_steps=observe_accepted_steps
    )
    started = perf_counter()
    result = _run_with_segment_solver(spec, segment_solver)
    elapsed_seconds = perf_counter() - started
    return CandidateRun(
        result=result,
        segments=tuple(segment_solver.observations),
        elapsed_seconds=elapsed_seconds,
    )


def _mechanics_assessment(candidate: CandidateRun) -> dict[str, object]:
    result = candidate.result
    spec = result.spec
    expected_cycle_count = int(round(spec.duration / spec.renormalization_interval))
    expected_boundaries = np.linspace(0.0, spec.duration, expected_cycle_count + 1)[1:]
    cycle_times_match = np.array_equal(result.cycle_end_time, expected_boundaries)
    positive_finite_stretches = bool(
        np.all(np.isfinite(result.stretch_factor))
        and np.all(result.stretch_factor > 0.0)
    )
    log_identity_error = float(
        np.max(np.abs(np.log(result.stretch_factor) - result.log_stretch_increment))
    )
    cumulative_identity_error = float(
        np.max(
            np.abs(
                np.cumsum(result.log_stretch_increment)
                - result.cumulative_log_stretch
            )
        )
    )
    rate_identity_error = abs(
        result.finite_time_stretching_rate
        - result.cumulative_log_stretch[-1] / spec.duration
    )
    segment_count_matches = (
        len(candidate.segments)
        == result.diagnostics.segment_count
        == expected_cycle_count
    )
    accepted_times_monotonic = all(
        np.all(np.diff(segment.accepted_time) > 0.0)
        for segment in candidate.segments
    )
    accepted_steps_observed = all(
        segment.accepted_steps_observed for segment in candidate.segments
    )
    endpoints_reached = all(
        math.isclose(
            segment.accepted_time[-1],
            segment.end_time,
            rel_tol=0.0,
            abs_tol=TIME_ABSOLUTE_TOLERANCE,
        )
        for segment in candidate.segments
    )
    finite_states = all(
        np.all(np.isfinite(segment.accepted_state))
        for segment in candidate.segments
    )
    maximum_step_gap = candidate.maximum_accepted_step_gap
    max_step_enforced = maximum_step_gap <= (
        result.diagnostics.max_step_seconds
        + MAX_STEP_FLOATING_POINT_ALLOWANCE
        * max(1.0, abs(result.diagnostics.max_step_seconds))
    )
    reset_norm_valid = (
        result.diagnostics.maximum_post_renormalization_norm_error
        <= spec.renormalization_norm_tolerance
    )
    return_codes_successful = all(
        segment.return_code == 1 for segment in candidate.segments
    )
    all_checks_passed = all(
        (
            cycle_times_match,
            positive_finite_stretches,
            segment_count_matches,
            accepted_times_monotonic,
            accepted_steps_observed,
            endpoints_reached,
            finite_states,
            max_step_enforced,
            reset_norm_valid,
            return_codes_successful,
            log_identity_error <= 2.0e-15,
            cumulative_identity_error <= 2.0e-15,
            rate_identity_error <= 2.0e-15,
        )
    )
    return {
        "all_checks_passed": all_checks_passed,
        "cycle_count": result.diagnostics.segment_count,
        "cycle_times_match_exactly": cycle_times_match,
        "positive_finite_stretch_factors": positive_finite_stretches,
        "maximum_log_identity_error": log_identity_error,
        "maximum_cumulative_log_identity_error": cumulative_identity_error,
        "finite_time_rate_identity_error_per_second": rate_identity_error,
        "maximum_post_reset_candidate_a_norm_error": (
            result.diagnostics.maximum_post_renormalization_norm_error
        ),
        "accepted_times_strictly_monotonic": accepted_times_monotonic,
        "accepted_steps_observed": accepted_steps_observed,
        "all_segment_endpoints_reached": endpoints_reached,
        "all_accepted_states_finite": finite_states,
        "return_codes_successful": return_codes_successful,
        "accepted_step_count": candidate.accepted_step_count,
        "maximum_accepted_step_gap_seconds": maximum_step_gap,
        "declared_max_step_seconds": result.diagnostics.max_step_seconds,
        "max_step_enforced": max_step_enforced,
    }


def assess_equivalence() -> list[dict[str, object]]:
    """Compare the candidate with the compiled-RHS solve_ivp oracle."""

    assessments = []
    for angle_pair in VALIDATION_ANGLE_PAIRS_DEGREES:
        spec = validation_spec(*angle_pair)
        oracle = run_renormalized_tangent_compiled(spec)
        candidate = run_fortran_candidate(spec)
        comparison = compare_results(oracle, candidate.result)
        mechanics = _mechanics_assessment(candidate)
        energy_below_limit = (
            oracle.diagnostics.maximum_normalized_reference_energy_drift
            <= spec.energy_drift_limit
            and candidate.result.diagnostics.maximum_normalized_reference_energy_drift
            <= spec.energy_drift_limit
        )
        accepted = bool(
            comparison["accepted"]
            and mechanics["all_checks_passed"]
            and energy_below_limit
        )
        assessments.append(
            {
                "theta1_degrees": angle_pair[0],
                "theta2_degrees": angle_pair[1],
                **comparison,
                "accepted": accepted,
                "oracle_energy_sampling": "uniform 0.01 s diagnostic grid",
                "candidate_energy_sampling": "accepted Fortran DOP853 steps",
                "both_energy_diagnostics_below_limit": energy_below_limit,
                "energy_drift_limit": spec.energy_drift_limit,
                "oracle_maximum_normalized_energy_drift": (
                    oracle.diagnostics.maximum_normalized_reference_energy_drift
                ),
                "candidate_maximum_normalized_energy_drift": (
                    candidate.result.diagnostics.maximum_normalized_reference_energy_drift
                ),
                "candidate_segment_solver_seconds": (
                    candidate.segment_solver_seconds
                ),
                "candidate_accepted_step_count": candidate.accepted_step_count,
                "candidate_maximum_accepted_step_gap_seconds": (
                    candidate.maximum_accepted_step_gap
                ),
                "candidate_warning_messages": sorted(
                    {
                        message
                        for segment in candidate.segments
                        for message in segment.warning_messages
                    }
                ),
                "mechanics": mechanics,
            }
        )
    return assessments


def _timed_prototype_mode(
    spec: RenormalizedTangentSpec,
    segment_solver: SegmentSolver,
) -> tuple[RenormalizedTangentResult, float, float]:
    timed_solver = TimedSegmentSolver(segment_solver)
    started = perf_counter()
    result = _run_with_segment_solver(spec, timed_solver)
    elapsed = perf_counter() - started
    return result, elapsed, float(sum(timed_solver.elapsed_seconds))


def _distribution(values: list[float]) -> dict[str, object]:
    array = np.asarray(values, dtype=float)
    return {
        "sample_count": len(values),
        "median_seconds": float(median(values)),
        "interquartile_range_seconds": float(
            np.percentile(array, 75.0) - np.percentile(array, 25.0)
        ),
        "minimum_seconds": float(np.min(array)),
        "maximum_seconds": float(np.max(array)),
        "seconds": values,
    }


def _count_summary(values: list[int]) -> dict[str, object]:
    return {
        "sample_count": len(values),
        "minimum": min(values),
        "median": float(median(values)),
        "maximum": max(values),
        "counts": values,
    }


def benchmark_modes(repeats: int) -> dict[str, object]:
    """Measure the three declared modes and observation overhead."""

    if repeats <= 0:
        raise ValueError("Benchmark repeats must be positive.")
    complete_times: dict[str, list[float]] = {
        "solve_ivp_oracle": [],
        "solve_ivp_endpoint_only_control": [],
        "fortran_dop853_candidate": [],
        "fortran_dop853_without_step_observation_control": [],
    }
    segment_times = {name: [] for name in complete_times}
    function_evaluations: dict[str, list[int]] = {
        name: [] for name in complete_times
    }
    observed_accepted_steps: list[int] = []

    mode_names = tuple(complete_times)
    for repeat in range(repeats):
        for case_index, angle_pair in enumerate(BENCHMARK_ANGLE_PAIRS_DEGREES):
            spec = validation_spec(*angle_pair)
            offset = (repeat + case_index) % len(mode_names)
            ordered_modes = mode_names[offset:] + mode_names[:offset]
            for mode in ordered_modes:
                if mode == "solve_ivp_oracle":
                    result, elapsed, solver_elapsed = _timed_prototype_mode(
                        spec, _solve_segment
                    )
                elif mode == "solve_ivp_endpoint_only_control":
                    result, elapsed, solver_elapsed = _timed_prototype_mode(
                        spec, solve_ivp_endpoint_only_segment
                    )
                else:
                    observed = mode == "fortran_dop853_candidate"
                    candidate = run_fortran_candidate(
                        spec, observe_accepted_steps=observed
                    )
                    result = candidate.result
                    elapsed = candidate.elapsed_seconds
                    solver_elapsed = candidate.segment_solver_seconds
                    if observed:
                        observed_accepted_steps.append(
                            candidate.accepted_step_count
                        )
                complete_times[mode].append(elapsed)
                segment_times[mode].append(solver_elapsed)
                function_evaluations[mode].append(
                    result.diagnostics.solver_function_evaluations
                )

    complete = {
        name: _distribution(values) for name, values in complete_times.items()
    }
    segment = {
        name: _distribution(values) for name, values in segment_times.items()
    }
    oracle_median = complete["solve_ivp_oracle"]["median_seconds"]
    candidate_median = complete["fortran_dop853_candidate"]["median_seconds"]
    unobserved_median = complete[
        "fortran_dop853_without_step_observation_control"
    ]["median_seconds"]
    return {
        "benchmark_angle_pairs_degrees": [
            list(pair) for pair in BENCHMARK_ANGLE_PAIRS_DEGREES
        ],
        "repeats": repeats,
        "interleaved_order": True,
        "complete_observable": complete,
        "segment_solver": segment,
        "rhs_function_evaluations": {
            name: _count_summary(values)
            for name, values in function_evaluations.items()
        },
        "candidate_observed_accepted_steps": _count_summary(
            observed_accepted_steps
        ),
        "warmed_complete_observable_speedup": oracle_median / candidate_median,
        "material_speedup_gate": MATERIAL_SPEEDUP_GATE,
        "material_speedup_gate_passed": (
            oracle_median / candidate_median >= MATERIAL_SPEEDUP_GATE
        ),
        "accepted_step_observation_overhead_seconds": (
            candidate_median - unobserved_median
        ),
        "accepted_step_observation_overhead_ratio": (
            candidate_median / unobserved_median
        ),
        "profiling_controls_are_not_scientific_candidates": True,
    }


def _warm_numba_kernel() -> dict[str, object]:
    spec = validation_spec(*VALIDATION_ANGLE_PAIRS_DEGREES[0])
    parameters = spec.parameters
    augmented = np.concatenate(
        (spec.initial_state.as_array(), np.asarray(spec.initial_tangent, dtype=float))
    )
    compilation_was_required = not bool(
        compiled_reference_and_tangent_rhs.signatures
    )
    started = perf_counter()
    value = compiled_reference_and_tangent_rhs(
        0.0,
        augmented,
        parameters.length1,
        parameters.length2,
        parameters.mass1,
        parameters.mass2,
        parameters.gravity,
    )
    elapsed = perf_counter() - started
    if not np.all(np.isfinite(value)):
        raise RuntimeError("Numba warm-up returned non-finite values.")
    return {
        "compilation_was_required": compilation_was_required,
        "first_kernel_call_seconds": elapsed,
        "nopython_signature_count": len(
            compiled_reference_and_tangent_rhs.nopython_signatures
        ),
    }


def run_assessment(benchmark_repeats: int = 7) -> dict[str, object]:
    """Execute the bounded scientific and performance assessment."""

    numba_timing = _warm_numba_kernel()
    center_spec = validation_spec(*VALIDATION_ANGLE_PAIRS_DEGREES[0])
    started = perf_counter()
    first_fortran = run_fortran_candidate(center_spec)
    first_fortran_seconds = perf_counter() - started

    comparisons = assess_equivalence()
    performance = benchmark_modes(benchmark_repeats)
    all_equivalence_gates_passed = all(item["accepted"] for item in comparisons)
    all_energy_gates_passed = all(
        item["both_energy_diagnostics_below_limit"]
        and item["energy_diagnostic_absolute_error"]
        <= ENERGY_DIAGNOSTIC_ABSOLUTE_TOLERANCE
        for item in comparisons
    )
    all_mechanics_gates_passed = all(
        item["mechanics"]["all_checks_passed"] for item in comparisons
    )
    verdict = (
        "ACCEPT"
        if all_equivalence_gates_passed
        and all_energy_gates_passed
        and all_mechanics_gates_passed
        and performance["material_speedup_gate_passed"]
        else "REJECT"
    )
    return {
        "experiment": "015_compiled_integration_boundary",
        "question": (
            "Can SciPy's compiled Fortran DOP853 segment integrator replace "
            "the Python solve_ivp boundary for the accepted fixed-horizon "
            "renormalized tangent observable?"
        ),
        "verdict": verdict,
        "oracle": "Numba RHS/JVP with Python solve_ivp DOP853",
        "candidate": (
            "Numba RHS/JVP with SciPy Fortran DOP853, one call per "
            "renormalisation interval"
        ),
        "scientific_contract": {
            "duration_seconds": center_spec.duration,
            "renormalization_interval_seconds": (
                center_spec.renormalization_interval
            ),
            "sampling_interval_seconds": center_spec.sampling_interval,
            "initial_tangent": list(center_spec.initial_tangent),
            "initial_angular_velocities_radians_per_second": [0.0, 0.0],
            "solver_method_family": center_spec.solver.method,
            "solver_rtol": center_spec.solver.rtol,
            "solver_atol": center_spec.solver.atol,
            "resolved_max_step_seconds": (
                first_fortran.result.diagnostics.max_step_seconds
            ),
            "energy_drift_limit": center_spec.energy_drift_limit,
            "renormalization_norm_tolerance": (
                center_spec.renormalization_norm_tolerance
            ),
        },
        "predeclared_gates": {
            "rate_absolute_error_per_second": RATE_ABSOLUTE_TOLERANCE,
            "cycle_log_absolute_error": CYCLE_LOG_ABSOLUTE_TOLERANCE,
            "final_reference_candidate_a_distance": (
                FINAL_REFERENCE_DISTANCE_TOLERANCE
            ),
            "final_tangent_candidate_a_distance": (
                FINAL_TANGENT_DISTANCE_TOLERANCE
            ),
            "energy_diagnostic_absolute_error": (
                ENERGY_DIAGNOSTIC_ABSOLUTE_TOLERANCE
            ),
            "warmed_complete_observable_speedup": MATERIAL_SPEEDUP_GATE,
        },
        "validation_angle_pairs_degrees": [
            list(pair) for pair in VALIDATION_ANGLE_PAIRS_DEGREES
        ],
        "all_equivalence_gates_passed": all_equivalence_gates_passed,
        "all_energy_gates_passed": all_energy_gates_passed,
        "all_mechanics_gates_passed": all_mechanics_gates_passed,
        "comparisons": comparisons,
        "energy_sampling": {
            "oracle": "uniform 0.01 s diagnostic grid",
            "candidate": "accepted Fortran DOP853 steps",
            "reference_contract_redefined": False,
            "interpretation": (
                "The candidate diagnostic is accepted only because its maximum "
                "step gap does not exceed the declared max_step, both paths "
                "remain below the unchanged validity limit, and their reported "
                "maxima agree within the predeclared comparison tolerance."
            ),
        },
        "timing": {
            "numba_cold_compilation": numba_timing,
            "first_fortran_complete_evaluation_seconds": first_fortran_seconds,
            "warmed": performance,
        },
        "provenance": {
            "python_version": platform.python_version(),
            "numpy_version": np.__version__,
            "scipy_version": scipy.__version__,
            "numba_version": numba.__version__,
            "prototype_oracle_module": (
                "development.chaos_content.prototypes.lyapunov_exponents.compiled"
            ),
            "candidate_location": str(Path(__file__).resolve()),
        },
        "claim_boundary": {
            "fixed_horizon_observable_only": True,
            "asymptotic_lyapunov_exponent_claimed": False,
            "candidate_promoted_to_prototype": False,
            "profiling_control_equivalence_claimed": False,
            "large_grid_or_batch_claimed": False,
        },
    }


def _json_default(value: object) -> object:
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"Cannot serialize {type(value).__name__}.")


def save_assessment(
    assessment: dict[str, object], path: Path = DEFAULT_EVIDENCE_PATH
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output:
        json.dump(
            assessment,
            output,
            indent=2,
            allow_nan=False,
            default=_json_default,
        )
        output.write("\n")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIRECTORY,
        help="Ignored directory for the machine-readable evidence bundle.",
    )
    parser.add_argument("--benchmark-repeats", type=int, default=7)
    arguments = parser.parse_args()
    assessment = run_assessment(arguments.benchmark_repeats)
    save_assessment(assessment, arguments.output_dir / "summary.json")
    return 0 if assessment["verdict"] == "ACCEPT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
