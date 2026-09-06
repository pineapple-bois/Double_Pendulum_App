"""Bounded attribution profile for the promoted compiled first-flip route.

The probe times the existing production evaluator and temporarily wraps the
SciPy DOP853/event boundary.  It does not replace the solver, alter its inputs,
or change the first-flip contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import subprocess
from contextlib import ExitStack
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Mapping
from unittest.mock import patch

import numba
import numpy as np
import scipy
import scipy.integrate._ivp.ivp as scipy_ivp
from scipy.integrate._ivp.rk import DOP853, Dop853DenseOutput

from ....src.first_flip import compiled as compiled_module
from ....src.first_flip import reference as reference_module
from ....src.first_flip.reference import FirstFlipResult
from ....src.lyapunov.reference import EulerLagrangeState


PERFORMANCE_DIRECTORY = Path(__file__).resolve().parents[1]
DEFAULT_CASE_EVIDENCE = (
    PERFORMANCE_DIRECTORY
    / "evidence"
    / "current"
    / "first_flip_compiled_rhs_feasibility.json"
)
DEFAULT_FIELD_EVIDENCE = (
    PERFORMANCE_DIRECTORY
    / "evidence"
    / "current"
    / "first_flip_compiled_promotion_64.json"
)
DEFAULT_OUTPUT = (
    PERFORMANCE_DIRECTORY
    / "evidence"
    / "current"
    / "first_flip_post_promotion_profile.json"
)
EVENT_TIME_GATE_SECONDS = 5.0e-8


@dataclass(frozen=True)
class ProfileCase:
    name: str
    outcome: str
    theta1_radians: float
    theta2_radians: float

    def state(self) -> EulerLagrangeState:
        return EulerLagrangeState(
            self.theta1_radians,
            self.theta2_radians,
            0.0,
            0.0,
        )


@dataclass
class Timings:
    seconds: float = 0.0
    calls: int = 0

    def add(self, seconds: float) -> None:
        self.seconds += seconds
        self.calls += 1


@dataclass
class ProfileCounters:
    rhs: Timings = field(default_factory=Timings)
    rhs_in_step: Timings = field(default_factory=Timings)
    rhs_in_dense_build: Timings = field(default_factory=Timings)
    events: Timings = field(default_factory=Timings)
    events_in_root: Timings = field(default_factory=Timings)
    steps: Timings = field(default_factory=Timings)
    dense_build: Timings = field(default_factory=Timings)
    dense_evaluation: Timings = field(default_factory=Timings)
    dense_evaluation_in_root: Timings = field(default_factory=Timings)
    root_location: Timings = field(default_factory=Timings)
    active_event_detection: Timings = field(default_factory=Timings)
    helpers: dict[str, Timings] = field(default_factory=dict)
    solver_clock_samples: list[float] = field(default_factory=list)
    step_depth: int = 0
    dense_build_depth: int = 0
    root_depth: int = 0


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_output(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments], capture_output=True, check=False, text=True
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unavailable"


def _median(values: list[float]) -> float:
    return float(statistics.median(values))


def _load_cases(path: Path) -> tuple[ProfileCase, ...]:
    payload = json.loads(path.read_text())
    records = [record for record in payload["cases"] if record["weighting_sample"]]
    cases = tuple(
        ProfileCase(
            name=str(record["name"]),
            outcome=str(record["outcome"]),
            theta1_radians=float(record["theta1_radians"]),
            theta2_radians=float(record["theta2_radians"]),
        )
        for record in records
    )
    outcomes = [case.outcome for case in cases]
    if outcomes.count("observed") != 16 or outcomes.count("censored") != 16:
        raise ValueError("Expected the validated 16 observed and 16 censored cases")
    return cases


def _timed_rhs(
    function: Callable[[float, np.ndarray], np.ndarray],
    counters: ProfileCounters,
) -> Callable[[float, np.ndarray], np.ndarray]:
    def evaluate(time_value: float, state: np.ndarray) -> np.ndarray:
        started = perf_counter()
        try:
            return function(time_value, state)
        finally:
            elapsed = perf_counter() - started
            counters.rhs.add(elapsed)
            if counters.step_depth:
                counters.rhs_in_step.add(elapsed)
            if counters.dense_build_depth:
                counters.rhs_in_dense_build.add(elapsed)

    return evaluate


def _timed_event_factory(
    original: Callable[[np.ndarray], tuple[Callable[..., float], ...]],
    counters: ProfileCounters,
) -> Callable[[np.ndarray], tuple[Callable[..., float], ...]]:
    def build(initial_state: np.ndarray) -> tuple[Callable[..., float], ...]:
        events = original(initial_state)
        wrapped: list[Callable[..., float]] = []
        for event in events:
            def evaluate(
                time_value: float,
                state: np.ndarray,
                *,
                _event: Callable[..., float] = event,
            ) -> float:
                started = perf_counter()
                try:
                    return float(_event(time_value, state))
                finally:
                    elapsed = perf_counter() - started
                    counters.events.add(elapsed)
                    if counters.root_depth:
                        counters.events_in_root.add(elapsed)

            evaluate.terminal = event.terminal  # type: ignore[attr-defined]
            evaluate.direction = event.direction  # type: ignore[attr-defined]
            wrapped.append(evaluate)
        return tuple(wrapped)

    return build


def _timed_helper(
    name: str,
    original: Callable[..., Any],
    counters: ProfileCounters,
) -> Callable[..., Any]:
    def evaluate(*args: Any, **kwargs: Any) -> Any:
        started = perf_counter()
        try:
            return original(*args, **kwargs)
        finally:
            counters.helpers.setdefault(name, Timings()).add(
                perf_counter() - started
            )

    return evaluate


def _profile_once(case: ProfileCase) -> tuple[FirstFlipResult, dict[str, Any]]:
    counters = ProfileCounters()
    parameters = reference_module.PendulumParameters()
    solver = reference_module.default_solver_spec(parameters)
    production_rhs = compiled_module.initialize_compiled_rhs(parameters)
    timed_rhs = _timed_rhs(production_rhs, counters)

    original_event_factory = reference_module._event_functions
    original_step = DOP853._step_impl
    original_dense_build = DOP853._dense_output_impl
    original_dense_evaluation = Dop853DenseOutput._call_impl
    original_root_location = scipy_ivp.solve_event_equation
    original_active_event_detection = scipy_ivp.find_active_events

    def timed_step(instance: DOP853) -> tuple[bool, str | None]:
        counters.step_depth += 1
        started = perf_counter()
        try:
            return original_step(instance)
        finally:
            counters.steps.add(perf_counter() - started)
            counters.step_depth -= 1

    def timed_dense_build(instance: DOP853) -> Dop853DenseOutput:
        counters.dense_build_depth += 1
        started = perf_counter()
        try:
            return original_dense_build(instance)
        finally:
            counters.dense_build.add(perf_counter() - started)
            counters.dense_build_depth -= 1

    def timed_dense_evaluation(
        instance: Dop853DenseOutput, time_value: np.ndarray
    ) -> np.ndarray:
        started = perf_counter()
        try:
            return original_dense_evaluation(instance, time_value)
        finally:
            elapsed = perf_counter() - started
            counters.dense_evaluation.add(elapsed)
            if counters.root_depth:
                counters.dense_evaluation_in_root.add(elapsed)

    def timed_root_location(
        event: Callable[..., float],
        solution: Callable[..., np.ndarray],
        time_old: float,
        time_new: float,
    ) -> float:
        counters.root_depth += 1
        started = perf_counter()
        try:
            return float(
                original_root_location(event, solution, time_old, time_new)
            )
        finally:
            counters.root_location.add(perf_counter() - started)
            counters.root_depth -= 1

    def timed_active_event_detection(
        values_old: np.ndarray,
        values_new: np.ndarray,
        directions: np.ndarray,
    ) -> np.ndarray:
        started = perf_counter()
        try:
            return original_active_event_detection(
                values_old, values_new, directions
            )
        finally:
            counters.active_event_detection.add(perf_counter() - started)

    def solver_clock() -> float:
        value = perf_counter()
        counters.solver_clock_samples.append(value)
        return value

    helper_names = (
        "structural_validation",
        "event_records",
        "surface_value",
        "maximum_angular_increment",
        "energy",
    )
    helper_functions = (
        reference_module._structural_validation_issues,
        reference_module._event_records,
        reference_module._surface_value,
        reference_module._maximum_angular_increment,
        reference_module.simple_energy,
    )

    with ExitStack() as stack:
        stack.enter_context(
            patch.object(compiled_module, "initialize_compiled_rhs", lambda _p: timed_rhs)
        )
        stack.enter_context(
            patch.object(
                reference_module,
                "_event_functions",
                _timed_event_factory(original_event_factory, counters),
            )
        )
        stack.enter_context(patch.object(DOP853, "_step_impl", timed_step))
        stack.enter_context(
            patch.object(DOP853, "_dense_output_impl", timed_dense_build)
        )
        stack.enter_context(
            patch.object(Dop853DenseOutput, "_call_impl", timed_dense_evaluation)
        )
        stack.enter_context(
            patch.object(scipy_ivp, "solve_event_equation", timed_root_location)
        )
        stack.enter_context(
            patch.object(
                scipy_ivp, "find_active_events", timed_active_event_detection
            )
        )
        stack.enter_context(patch.object(reference_module, "perf_counter", solver_clock))
        for name, function in zip(helper_names, helper_functions, strict=True):
            attribute = {
                "structural_validation": "_structural_validation_issues",
                "event_records": "_event_records",
                "surface_value": "_surface_value",
                "maximum_angular_increment": "_maximum_angular_increment",
                "energy": "simple_energy",
            }[name]
            stack.enter_context(
                patch.object(
                    reference_module,
                    attribute,
                    _timed_helper(name, function, counters),
                )
            )

        outer_started = perf_counter()
        result = compiled_module.first_flip_time_compiled(
            case.state(),
            parameters=parameters,
            solver_spec=solver,
            observation_horizon=5.0,
        )
        outer_finished = perf_counter()

    if len(counters.solver_clock_samples) != 2:
        raise RuntimeError("Expected exactly two first_flip_time solver clocks")
    solver_started, solver_finished = counters.solver_clock_samples
    pre_solve = solver_started - outer_started
    post_solve = outer_finished - solver_finished
    rhs_seconds = counters.rhs.seconds
    step_non_rhs = max(0.0, counters.steps.seconds - counters.rhs_in_step.seconds)
    dense_build_non_rhs = max(
        0.0, counters.dense_build.seconds - counters.rhs_in_dense_build.seconds
    )
    root_algorithm = max(
        0.0,
        counters.root_location.seconds
        - counters.events_in_root.seconds
        - counters.dense_evaluation_in_root.seconds,
    )
    accounted_solver = (
        rhs_seconds
        + step_non_rhs
        + dense_build_non_rhs
        + counters.events.seconds
        + counters.dense_evaluation.seconds
        + root_algorithm
        + counters.active_event_detection.seconds
    )
    solver_orchestration = max(0.0, result.wall_seconds - accounted_solver)
    helper_seconds = {name: value.seconds for name, value in counters.helpers.items()}
    helper_calls = {name: value.calls for name, value in counters.helpers.items()}
    post_helpers = sum(helper_seconds.values())
    return result, {
        "evaluator_seconds": outer_finished - outer_started,
        "pre_solve_seconds": pre_solve,
        "solve_ivp_seconds": result.wall_seconds,
        "post_solve_seconds": post_solve,
        "rhs_seconds": rhs_seconds,
        "dop853_step_outside_rhs_seconds": step_non_rhs,
        "dense_output_build_outside_rhs_seconds": dense_build_non_rhs,
        "event_callback_seconds": counters.events.seconds,
        "dense_output_evaluation_seconds": counters.dense_evaluation.seconds,
        "root_algorithm_outside_event_and_dense_seconds": root_algorithm,
        "active_event_detection_seconds": counters.active_event_detection.seconds,
        "solve_ivp_orchestration_residual_seconds": solver_orchestration,
        "post_solve_helper_seconds": helper_seconds,
        "post_solve_residual_seconds": max(0.0, post_solve - post_helpers),
        "counts": {
            "rhs": counters.rhs.calls,
            "accepted_steps": counters.steps.calls,
            "event_callbacks": counters.events.calls,
            "event_callbacks_during_root": counters.events_in_root.calls,
            "dense_output_builds": counters.dense_build.calls,
            "dense_output_evaluations": counters.dense_evaluation.calls,
            "root_locations": counters.root_location.calls,
            "active_event_detection_calls": counters.active_event_detection.calls,
            "post_solve_helpers": helper_calls,
        },
    }


def _baseline_once(case: ProfileCase) -> tuple[FirstFlipResult, float]:
    parameters = reference_module.PendulumParameters()
    solver = reference_module.default_solver_spec(parameters)
    started = perf_counter()
    result = compiled_module.first_flip_time_compiled(
        case.state(),
        parameters=parameters,
        solver_spec=solver,
        observation_horizon=5.0,
    )
    return result, perf_counter() - started


def _results_agree(left: FirstFlipResult, right: FirstFlipResult) -> bool:
    if (
        left.status is not right.status
        or left.event_observed != right.event_observed
        or left.censored != right.censored
        or left.event_identities != right.event_identities
        or left.raw_event_counts != right.raw_event_counts
        or left.rhs_evaluations != right.rhs_evaluations
    ):
        return False
    if left.event_time_seconds is None or right.event_time_seconds is None:
        return left.event_time_seconds is right.event_time_seconds
    return abs(left.event_time_seconds - right.event_time_seconds) <= EVENT_TIME_GATE_SECONDS


def _median_mapping(records: list[dict[str, Any]]) -> dict[str, Any]:
    scalar_names = (
        "evaluator_seconds",
        "pre_solve_seconds",
        "solve_ivp_seconds",
        "post_solve_seconds",
        "rhs_seconds",
        "dop853_step_outside_rhs_seconds",
        "dense_output_build_outside_rhs_seconds",
        "event_callback_seconds",
        "dense_output_evaluation_seconds",
        "root_algorithm_outside_event_and_dense_seconds",
        "active_event_detection_seconds",
        "solve_ivp_orchestration_residual_seconds",
        "post_solve_residual_seconds",
    )
    result: dict[str, Any] = {
        name: _median([float(record[name]) for record in records])
        for name in scalar_names
    }
    helper_names = records[0]["post_solve_helper_seconds"].keys()
    result["post_solve_helper_seconds"] = {
        name: _median(
            [float(record["post_solve_helper_seconds"][name]) for record in records]
        )
        for name in helper_names
    }
    count_names = records[0]["counts"].keys()
    result["counts"] = {
        name: _median([float(record["counts"][name]) for record in records])
        for name in count_names
        if name != "post_solve_helpers"
    }
    return result


def _group_mean(cases: list[dict[str, Any]], key: str) -> float:
    return statistics.fmean(float(case["profile_median"][key]) for case in cases)


def _instrumentation_adjusted_components(
    baseline_evaluator: float,
    profiled_evaluator: float,
    components: Mapping[str, float],
) -> tuple[float, dict[str, float]]:
    """Conservatively remove measured probe inflation from uncertain buckets."""

    excess = max(0.0, profiled_evaluator - baseline_evaluator)
    adjusted = dict(components)
    uncertain_names = (
        "dop853_step_outside_rhs_seconds",
        "solve_ivp_orchestration_residual_seconds",
    )
    uncertain_total = sum(adjusted[name] for name in uncertain_names)
    correction = min(excess, uncertain_total)
    if uncertain_total:
        for name in uncertain_names:
            adjusted[name] -= correction * adjusted[name] / uncertain_total
    return excess, adjusted


def _scenario(
    baseline_total: float,
    baseline_evaluation: float,
    removable_fraction: float,
    acceleration: float | None,
    *,
    scalable_evaluation: float | None = None,
) -> dict[str, float | str]:
    scalable = baseline_evaluation if scalable_evaluation is None else scalable_evaluation
    fixed_evaluation = baseline_evaluation - scalable
    retained_fraction = 1.0 - removable_fraction
    if acceleration is None:
        new_evaluation = fixed_evaluation + scalable * retained_fraction
        label = "infinite"
    else:
        new_evaluation = fixed_evaluation + scalable * (
            retained_fraction + removable_fraction / acceleration
        )
        label = f"{acceleration:g}x"
    new_total = baseline_total - baseline_evaluation + new_evaluation
    return {
        "removable_component_acceleration": label,
        "estimated_evaluation_seconds": new_evaluation,
        "estimated_total_seconds": new_total,
        "estimated_whole_field_speedup": baseline_total / new_total,
    }


def run_profile(
    case_evidence_path: Path,
    field_evidence_path: Path,
    repetitions: int,
) -> dict[str, Any]:
    cases = _load_cases(case_evidence_path)
    field_evidence = json.loads(field_evidence_path.read_text())
    parameters = reference_module.PendulumParameters()
    compiled_module.initialize_compiled_rhs(parameters)

    case_records: list[dict[str, Any]] = []
    all_agree = True
    for case_index, case in enumerate(cases):
        baseline_result, _ = _baseline_once(case)
        baseline_seconds: list[float] = []
        profile_records: list[dict[str, Any]] = []
        profile_agreement: list[bool] = []
        for repetition in range(repetitions):
            if (case_index + repetition) % 2 == 0:
                current, elapsed = _baseline_once(case)
                profiled, profile = _profile_once(case)
            else:
                profiled, profile = _profile_once(case)
                current, elapsed = _baseline_once(case)
            baseline_seconds.append(elapsed)
            profile_records.append(profile)
            profile_agreement.append(
                _results_agree(baseline_result, current)
                and _results_agree(baseline_result, profiled)
            )
        agreed = all(profile_agreement)
        all_agree = all_agree and agreed
        case_records.append(
            {
                "name": case.name,
                "outcome": case.outcome,
                "theta1_radians": case.theta1_radians,
                "theta2_radians": case.theta2_radians,
                "event_time_seconds": baseline_result.event_time_seconds,
                "rhs_evaluations": baseline_result.rhs_evaluations,
                "accepted_point_count": baseline_result.accepted_point_count,
                "baseline_evaluator_seconds": baseline_seconds,
                "baseline_evaluator_median_seconds": _median(baseline_seconds),
                "profile_median": _median_mapping(profile_records),
                "profile_instrumentation_factor": (
                    _median([float(item["evaluator_seconds"]) for item in profile_records])
                    / _median(baseline_seconds)
                ),
                "profile_preserved_result": agreed,
            }
        )

    grouped: dict[str, dict[str, Any]] = {}
    component_names = (
        "rhs_seconds",
        "dop853_step_outside_rhs_seconds",
        "dense_output_build_outside_rhs_seconds",
        "event_callback_seconds",
        "dense_output_evaluation_seconds",
        "root_algorithm_outside_event_and_dense_seconds",
        "active_event_detection_seconds",
        "solve_ivp_orchestration_residual_seconds",
    )
    for outcome in ("observed", "censored"):
        selected = [case for case in case_records if case["outcome"] == outcome]
        baseline = statistics.fmean(
            float(case["baseline_evaluator_median_seconds"]) for case in selected
        )
        profile_total = _group_mean(selected, "evaluator_seconds")
        solve_total = _group_mean(selected, "solve_ivp_seconds")
        components = {name: _group_mean(selected, name) for name in component_names}
        grouped[outcome] = {
            "case_count": len(selected),
            "baseline_evaluator_mean_of_case_medians_seconds": baseline,
            "profiled_evaluator_mean_of_case_medians_seconds": profile_total,
            "profile_instrumentation_factor": profile_total / baseline,
            "solve_ivp_seconds": solve_total,
            "pre_solve_seconds": _group_mean(selected, "pre_solve_seconds"),
            "post_solve_seconds": _group_mean(selected, "post_solve_seconds"),
            "solver_components_seconds": components,
            "solver_components_fraction": {
                name: value / solve_total for name, value in components.items()
            },
            "post_solve_helper_seconds": {
                name: statistics.fmean(
                    float(case["profile_median"]["post_solve_helper_seconds"][name])
                    for case in selected
                )
                for name in selected[0]["profile_median"]["post_solve_helper_seconds"]
            },
            "rhs_evaluations": statistics.fmean(
                float(case["rhs_evaluations"]) for case in selected
            ),
            "accepted_point_count": statistics.fmean(
                float(case["accepted_point_count"]) for case in selected
            ),
            "event_callback_count": statistics.fmean(
                float(case["profile_median"]["counts"]["event_callbacks"])
                for case in selected
            ),
            "root_location_count": statistics.fmean(
                float(case["profile_median"]["counts"]["root_locations"])
                for case in selected
            ),
        }
        inflation, adjusted = _instrumentation_adjusted_components(
            baseline, profile_total, components
        )
        grouped[outcome]["instrumentation_excess_seconds"] = inflation
        grouped[outcome]["instrumentation_adjusted_solver_components_seconds"] = (
            adjusted
        )
        grouped[outcome]["instrumentation_adjusted_solver_components_fraction_of_baseline_evaluator"] = {
            name: value / baseline for name, value in adjusted.items()
        }

    first_comparison = field_evidence["pairs"][0]["comparison"]
    observed_fraction = float(first_comparison["observed_count"]) / 4096.0
    censored_fraction = float(first_comparison["censored_count"]) / 4096.0
    weighted_raw: dict[str, float] = {}
    weighted: dict[str, float] = {}
    for name in component_names:
        weighted_raw[name] = (
            observed_fraction * grouped["observed"]["solver_components_seconds"][name]
            + censored_fraction * grouped["censored"]["solver_components_seconds"][name]
        )
        weighted[name] = (
            observed_fraction
            * grouped["observed"]["instrumentation_adjusted_solver_components_seconds"][name]
            + censored_fraction
            * grouped["censored"]["instrumentation_adjusted_solver_components_seconds"][name]
        )
    weighted_solve = (
        observed_fraction * grouped["observed"]["solve_ivp_seconds"]
        + censored_fraction * grouped["censored"]["solve_ivp_seconds"]
    )
    weighted_evaluator = (
        observed_fraction
        * grouped["observed"]["profiled_evaluator_mean_of_case_medians_seconds"]
        + censored_fraction
        * grouped["censored"]["profiled_evaluator_mean_of_case_medians_seconds"]
    )
    weighted_baseline_evaluator = (
        observed_fraction
        * grouped["observed"]["baseline_evaluator_mean_of_case_medians_seconds"]
        + censored_fraction
        * grouped["censored"]["baseline_evaluator_mean_of_case_medians_seconds"]
    )
    boundary_names = tuple(name for name in component_names if name != "rhs_seconds")
    boundary_seconds = sum(weighted[name] for name in boundary_names)
    adjusted_solve = sum(weighted.values())
    boundary_fraction_of_solver = boundary_seconds / adjusted_solve
    boundary_fraction_of_evaluator = boundary_seconds / weighted_baseline_evaluator

    compiled_field_totals = [
        float(pair["compiled"]["outer_wall_seconds"]) for pair in field_evidence["pairs"]
    ]
    compiled_field_evaluations = [
        float(pair["compiled"]["runner"]["evaluation_seconds"])
        for pair in field_evidence["pairs"]
    ]
    operational_total = statistics.median(compiled_field_totals)
    operational_evaluation = statistics.median(compiled_field_evaluations)
    process_width = int(field_evidence["workload"]["execution"]["process_width"])
    field_cell_count = int(field_evidence["workload"]["samples_per_axis"]) ** 2
    ideal_parallel_cell_compute = (
        weighted_baseline_evaluator * field_cell_count / process_width
    )
    scalable_evaluation = min(operational_evaluation, ideal_parallel_cell_compute)
    fixed_evaluation_residual = operational_evaluation - scalable_evaluation
    scenarios = [
        _scenario(
            operational_total,
            operational_evaluation,
            boundary_fraction_of_evaluator,
            acceleration,
            scalable_evaluation=scalable_evaluation,
        )
        for acceleration in (2.0, 3.0, 5.0, 10.0, None)
    ]
    required_new_evaluation = operational_total / 1.5 - (
        operational_total - operational_evaluation
    )
    required_scalable_fraction = (
        required_new_evaluation - fixed_evaluation_residual
    ) / scalable_evaluation
    denominator = required_scalable_fraction - (
        1.0 - boundary_fraction_of_evaluator
    )
    required_boundary_acceleration = (
        boundary_fraction_of_evaluator / denominator if denominator > 0.0 else float("inf")
    )
    decision = (
        "PROTOTYPE COMPILED SOLVER/EVENT LOOP"
        if required_boundary_acceleration <= 3.0
        else "STOP OPTIMIZING FIRST-FLIP T=5"
    )
    weighted_pre_solve = (
        observed_fraction * grouped["observed"]["pre_solve_seconds"]
        + censored_fraction * grouped["censored"]["pre_solve_seconds"]
    )
    weighted_post_solve = (
        observed_fraction * grouped["observed"]["post_solve_seconds"]
        + censored_fraction * grouped["censored"]["post_solve_seconds"]
    )
    ceiling_components = {
        **weighted,
        "pre_solve_seconds": weighted_pre_solve,
        "post_solve_seconds": weighted_post_solve,
    }
    component_ceilings = {
        name: {
            "seconds_per_representative_cell": seconds,
            "fraction_of_evaluator": seconds / weighted_baseline_evaluator,
            "whole_field_speedup_if_halved": _scenario(
                operational_total,
                operational_evaluation,
                seconds / weighted_baseline_evaluator,
                2.0,
                scalable_evaluation=scalable_evaluation,
            )["estimated_whole_field_speedup"],
            "whole_field_speedup_if_eliminated": _scenario(
                operational_total,
                operational_evaluation,
                seconds / weighted_baseline_evaluator,
                None,
                scalable_evaluation=scalable_evaluation,
            )["estimated_whole_field_speedup"],
        }
        for name, seconds in ceiling_components.items()
    }

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "attribute remaining promoted compiled first-flip evaluator cost",
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "numba": numba.__version__,
            "git_head": _git_output("rev-parse", "HEAD"),
            "git_status_short_before_artifact": _git_output("status", "--short"),
        },
        "inputs": {
            "case_evidence": str(case_evidence_path),
            "case_evidence_sha256": _sha256(case_evidence_path),
            "field_evidence": str(field_evidence_path),
            "field_evidence_sha256": _sha256(field_evidence_path),
            "repetitions": repetitions,
            "case_count": len(cases),
            "observed_fraction": observed_fraction,
            "censored_fraction": censored_fraction,
        },
        "contract": {
            "observation_horizon_seconds": 5.0,
            "parameters": "standard equal-link/unit-parameter",
            "initial_angular_velocities": [0.0, 0.0],
            "solver": "solve_ivp DOP853",
            "events": ["arm1-", "arm1+", "arm2-", "arm2+"],
            "terminal": True,
            "direction": 1.0,
            "event_time_agreement_gate_seconds": EVENT_TIME_GATE_SECONDS,
        },
        "method": {
            "component_times_are_inclusive": True,
            "components_are_non_overlapping_after_nested_time_subtraction": True,
            "baseline_is_uninstrumented": True,
            "profile_instrumentation_is_reported_separately": True,
            "result_agreement_all_cases": all_agree,
        },
        "cases": case_records,
        "groups": grouped,
        "weighted_profile": {
            "raw_profiled_solver_components_seconds": weighted_raw,
            "raw_profiled_solve_ivp_seconds": weighted_solve,
            "raw_profiled_evaluator_seconds": weighted_evaluator,
            "instrumentation_excess_seconds": (
                weighted_evaluator - weighted_baseline_evaluator
            ),
            "instrumentation_adjusted_solver_components_seconds": weighted,
            "instrumentation_adjusted_solve_ivp_seconds": adjusted_solve,
            "uninstrumented_evaluator_seconds": weighted_baseline_evaluator,
            "boundary_outside_rhs_seconds": boundary_seconds,
            "boundary_fraction_of_solve_ivp": boundary_fraction_of_solver,
            "boundary_fraction_of_evaluator": boundary_fraction_of_evaluator,
            "pre_solve_seconds": weighted_pre_solve,
            "post_solve_seconds": weighted_post_solve,
        },
        "operational_ceiling": {
            "baseline_median_64_total_seconds": operational_total,
            "baseline_median_64_evaluation_seconds": operational_evaluation,
            "baseline_non_evaluation_seconds": operational_total - operational_evaluation,
            "representative_cell_compute_at_four_worker_ideal_seconds": (
                ideal_parallel_cell_compute
            ),
            "fixed_operational_evaluation_residual_seconds": (
                fixed_evaluation_residual
            ),
            "assumption": (
                "profiled boundary fraction applies only to representative cell "
                "compute; compiled RHS, non-evaluation wall, and the difference "
                "between ideal four-worker cell compute and measured field "
                "evaluation wall are retained"
            ),
            "scenarios": scenarios,
            "component_ceilings": component_ceilings,
            "required_boundary_acceleration_for_1_5x_whole_field": (
                required_boundary_acceleration
            ),
            "theoretical_maximum_whole_field_speedup": scenarios[-1][
                "estimated_whole_field_speedup"
            ],
        },
        "decision": {
            "threshold_additional_whole_field_speedup": 1.5,
            "decision": decision,
            "prototype_justified": decision == "PROTOTYPE COMPILED SOLVER/EVENT LOOP",
        },
        "source_sha256": {str(Path(__file__)): _sha256(Path(__file__))},
    }


def save(payload: Mapping[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as target:
        json.dump(payload, target, indent=2, sort_keys=True, allow_nan=False)
        target.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-evidence", type=Path, default=DEFAULT_CASE_EVIDENCE)
    parser.add_argument("--field-evidence", type=Path, default=DEFAULT_FIELD_EVIDENCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--repetitions", type=int, default=5)
    return parser


def main(arguments: list[str] | None = None) -> int:
    options = build_parser().parse_args(arguments)
    if options.repetitions < 3:
        raise ValueError("At least three repetitions are required")
    if options.output.exists():
        raise FileExistsError(f"Refusing to replace profile evidence: {options.output}")
    payload = run_profile(
        options.case_evidence,
        options.field_evidence,
        options.repetitions,
    )
    save(payload, options.output)
    print(
        json.dumps(
            {
                "groups": payload["groups"],
                "weighted_profile": payload["weighted_profile"],
                "operational_ceiling": payload["operational_ceiling"],
                "decision": payload["decision"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if payload["method"]["result_agreement_all_cases"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
