"""Experiment-local audit of a verified solve_ivp fallback boundary."""

from __future__ import annotations

import argparse
import json
import math
import multiprocessing
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Iterable, Literal

import numpy as np


EXPERIMENT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
EXECUTION_EXPERIMENT_ROOT = (
    EXPERIMENT_ROOT.parents[1]
    / "execution_and_acceleration"
    / "016_independent_cell_execution_boundary"
)
for path in (REPOSITORY_ROOT, EXPERIMENT_ROOT, EXECUTION_EXPERIMENT_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import independent_cell_execution_boundary as execution
import max_step_audit as max_step_audit
import rectangular_work_unit_boundary as work_units
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.compiled import (
    COMPILED_EVALUATOR,
    compiled_rhs,
    evaluate_renormalized_tangent_compiled,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.compiled_equivalence import (
    VALIDATION_ANGLE_PAIRS_DEGREES,
    compare_results,
    validation_spec,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.compiled_dop853 import (
    COMPILED_DOP853_EVALUATOR,
    evaluate_renormalized_tangent_compiled_dop853,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.reference import (
    RenormalizedTangentSpec,
    _resolved_interval_max_step,
    _run_renormalized_tangent_with_rhs,
)
from development.chaos_content.prototypes.state_space_maps.src.state_space_fields import (
    EvaluationStatus,
    ScalarEvaluation,
)


FAST_ROUTE = "compiled_dop853"
FALLBACK_ROUTE = "compiled_rhs_solve_ivp_fallback"
FAST_ERROR_ROUTE = "compiled_dop853_execution_error"
SOLVE_IVP_CONTROL_ROUTE = "compiled_rhs_solve_ivp_control"
DEFAULT_EVIDENCE_PATH = (
    Path(__file__).resolve().parents[3]
    / "outputs"
    / "rectangular_work_unit_boundary"
    / "max_step_fallback_boundary.json"
)
BENCHMARK_REPEATS = 3
TILE_SHAPE = work_units.TileShape(8, 8)
_MAX_STEP_ERROR = re.compile(
    r"^compiled DOP853 exceeded the declared max_step: "
    r"(?P<observed>[0-9eE+.-]+) > (?P<declared>[0-9eE+.-]+)\.$"
)


@dataclass(frozen=True)
class EndpointSnapVerification:
    candidate_message_matched: bool
    verified: bool
    declared_max_step: float | None = None
    reported_maximum_gap: float | None = None
    violating_segments: tuple[int, ...] = ()
    maximum_observed_gap: float | None = None


@dataclass(frozen=True)
class HybridEvaluation:
    evaluation: ScalarEvaluation
    route: str
    elapsed_seconds: float
    fast_elapsed_seconds: float
    verification_elapsed_seconds: float = 0.0
    fallback_elapsed_seconds: float = 0.0
    fallback_reason: str | None = None
    verification: EndpointSnapVerification | None = None


@dataclass(frozen=True)
class HybridCellOutcome:
    task: execution.CellTask
    result: HybridEvaluation
    worker_pid: int


@dataclass(frozen=True)
class HybridFieldResult:
    samples: int
    mode: str
    tiled: bool
    values: np.ndarray
    status: np.ndarray
    route: np.ndarray
    outcomes: tuple[HybridCellOutcome, ...]
    elapsed_seconds: float


_WORKER_SPEC: RenormalizedTangentSpec | None = None


def _resolved_max_step(spec: RenormalizedTangentSpec) -> float:
    return _resolved_interval_max_step(
        spec.solver,
        spec.characteristic_length,
        spec.parameters.gravity,
        spec.renormalization_interval,
    )


def _candidate_endpoint_snap_error(
    evaluation: ScalarEvaluation,
    spec: RenormalizedTangentSpec,
) -> tuple[float, float] | None:
    if (
        evaluation.status is not EvaluationStatus.EXECUTION_ERROR
        or evaluation.evaluator != COMPILED_DOP853_EVALUATOR
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
    allowance = max_step_audit.MAX_STEP_FLOATING_POINT_ALLOWANCE * max(
        1.0,
        abs(expected),
    )
    if (
        declared != expected
        or not math.isfinite(observed)
        or observed <= declared + allowance
        or observed > 1.01 * declared + allowance
    ):
        return None
    return observed, declared


def verify_endpoint_snap_incompatibility(
    evaluation: ScalarEvaluation,
    spec: RenormalizedTangentSpec,
) -> EndpointSnapVerification:
    candidate = _candidate_endpoint_snap_error(evaluation, spec)
    if candidate is None:
        return EndpointSnapVerification(
            candidate_message_matched=False,
            verified=False,
        )
    reported_gap, declared = candidate
    tracer = max_step_audit.TracedFortranDop853Solver(spec)
    _run_renormalized_tangent_with_rhs(
        spec,
        compiled_rhs(spec.parameters),
        segment_solver=tracer,
    )
    violating = tuple(
        trace for trace in tracer.traces
        if trace.maximum_gap_exceeds_declared_limit
    )
    allowance = max_step_audit.MAX_STEP_FLOATING_POINT_ALLOWANCE * max(
        1.0,
        abs(declared),
    )
    verified = bool(
        violating
        and math.isclose(
            max(trace.maximum_step_gap for trace in violating),
            reported_gap,
            rel_tol=0.0,
            abs_tol=allowance,
        )
        and all(
            trace.successful
            and trace.return_code == 1
            and trace.endpoint_reached
            and trace.all_states_finite
            and trace.maximum_gap_is_endpoint_step
            and trace.maximum_step_gap <= 1.01 * declared + allowance
            and trace.configured_fortran_max_step == declared
            for trace in violating
        )
    )
    return EndpointSnapVerification(
        candidate_message_matched=True,
        verified=verified,
        declared_max_step=declared,
        reported_maximum_gap=reported_gap,
        violating_segments=tuple(trace.segment_number for trace in violating),
        maximum_observed_gap=max(
            (trace.maximum_step_gap for trace in violating),
            default=None,
        ),
    )


def evaluate_hybrid(spec: RenormalizedTangentSpec) -> HybridEvaluation:
    started = perf_counter()
    fast = evaluate_renormalized_tangent_compiled_dop853(spec)
    fast_elapsed = perf_counter() - started
    if fast.status is not EvaluationStatus.EXECUTION_ERROR:
        return HybridEvaluation(
            evaluation=fast,
            route=FAST_ROUTE,
            elapsed_seconds=perf_counter() - started,
            fast_elapsed_seconds=fast_elapsed,
        )

    verification_started = perf_counter()
    verification = verify_endpoint_snap_incompatibility(fast, spec)
    verification_elapsed = perf_counter() - verification_started
    if not verification.verified:
        return HybridEvaluation(
            evaluation=fast,
            route=FAST_ERROR_ROUTE,
            elapsed_seconds=perf_counter() - started,
            fast_elapsed_seconds=fast_elapsed,
            verification_elapsed_seconds=verification_elapsed,
            verification=verification,
        )

    fallback_started = perf_counter()
    fallback = evaluate_renormalized_tangent_compiled(spec)
    fallback_elapsed = perf_counter() - fallback_started
    return HybridEvaluation(
        evaluation=fallback,
        route=FALLBACK_ROUTE,
        elapsed_seconds=perf_counter() - started,
        fast_elapsed_seconds=fast_elapsed,
        verification_elapsed_seconds=verification_elapsed,
        fallback_elapsed_seconds=fallback_elapsed,
        fallback_reason="verified compiled-DOP853 endpoint max_step incompatibility",
        verification=verification,
    )


def _control_evaluation(
    spec: RenormalizedTangentSpec,
    mode: Literal["fast", "solve_ivp"],
) -> HybridEvaluation:
    started = perf_counter()
    if mode == "fast":
        evaluation = evaluate_renormalized_tangent_compiled_dop853(spec)
        route = (
            FAST_ROUTE
            if evaluation.status is not EvaluationStatus.EXECUTION_ERROR
            else FAST_ERROR_ROUTE
        )
    else:
        evaluation = evaluate_renormalized_tangent_compiled(spec)
        route = SOLVE_IVP_CONTROL_ROUTE
    elapsed = perf_counter() - started
    return HybridEvaluation(
        evaluation=evaluation,
        route=route,
        elapsed_seconds=elapsed,
        fast_elapsed_seconds=elapsed if mode == "fast" else 0.0,
        fallback_elapsed_seconds=elapsed if mode == "solve_ivp" else 0.0,
    )


def _initialize_worker(spec: RenormalizedTangentSpec) -> None:
    global _WORKER_SPEC
    _WORKER_SPEC = spec
    evaluate_renormalized_tangent_compiled_dop853(spec)
    evaluate_renormalized_tangent_compiled(spec)


def _evaluate_worker(payload: tuple[str, execution.CellTask]) -> HybridCellOutcome:
    if _WORKER_SPEC is None:
        raise RuntimeError("Fallback worker was not initialized.")
    mode, task = payload
    spec = execution.specification_for_task(task, _WORKER_SPEC)
    if mode == "hybrid":
        result = evaluate_hybrid(spec)
    elif mode in ("fast", "solve_ivp"):
        result = _control_evaluation(spec, mode)
    else:
        raise ValueError(f"Unknown execution mode: {mode}.")
    return HybridCellOutcome(task=task, result=result, worker_pid=os.getpid())


def _worker_identity() -> int:
    if _WORKER_SPEC is None:
        raise RuntimeError("Fallback worker was not initialized.")
    time.sleep(0.02)
    return os.getpid()


def _open_pool(spec: RenormalizedTangentSpec):
    executor = execution.ProcessPoolExecutor(
        max_workers=4,
        mp_context=multiprocessing.get_context("spawn"),
        initializer=_initialize_worker,
        initargs=(spec,),
    )
    identities: set[int] = set()
    for _attempt in range(8):
        futures = [executor.submit(_worker_identity) for _index in range(8)]
        identities.update(future.result() for future in futures)
        if len(identities) == 4:
            break
    if len(identities) != 4:
        executor.shutdown(wait=True, cancel_futures=True)
        raise RuntimeError("The fallback pool did not start four distinct workers.")
    return executor, tuple(sorted(identities))


def _execute_tasks(executor, mode: str, tasks: Iterable[execution.CellTask]):
    return tuple(
        executor.map(
            _evaluate_worker,
            ((mode, task) for task in tasks),
            chunksize=1,
        )
    )


def _assemble_field(
    samples: int,
    mode: str,
    tiled: bool,
    outcomes: Iterable[HybridCellOutcome],
    elapsed_seconds: float,
) -> HybridFieldResult:
    ordered = tuple(sorted(outcomes, key=lambda item: item.task.linear_index))
    if len(ordered) != samples * samples or any(
        item.task.linear_index != index for index, item in enumerate(ordered)
    ):
        raise ValueError("Field outcomes do not cover every indexed cell exactly once.")
    values = np.full((samples, samples), np.nan, dtype=float)
    status = np.empty((samples, samples), dtype="U24")
    route = np.empty((samples, samples), dtype="U40")
    for item in ordered:
        y_index = item.task.theta2_index
        x_index = item.task.theta1_index
        evaluation = item.result.evaluation
        if evaluation.value is not None:
            values[y_index, x_index] = evaluation.value
        status[y_index, x_index] = evaluation.status.value
        route[y_index, x_index] = item.result.route
    return HybridFieldResult(
        samples=samples,
        mode=mode,
        tiled=tiled,
        values=values,
        status=status,
        route=route,
        outcomes=ordered,
        elapsed_seconds=elapsed_seconds,
    )


def execute_untiled(samples: int, mode: str) -> HybridFieldResult:
    spec = RenormalizedTangentSpec()
    executor, identities = _open_pool(spec)
    try:
        started = perf_counter()
        outcomes = _execute_tasks(executor, mode, execution.grid_tasks(samples))
        elapsed = perf_counter() - started
    finally:
        executor.shutdown(wait=True, cancel_futures=True)
    if not all(not execution._pid_alive(process_id) for process_id in identities):
        raise RuntimeError("Fallback workers did not stop cleanly.")
    return _assemble_field(samples, mode, False, outcomes, elapsed)


def execute_tiled(samples: int) -> HybridFieldResult:
    spec = RenormalizedTangentSpec()
    context = work_units.bounded_field_context(samples, spec)
    executor, identities = _open_pool(spec)
    outcomes: list[HybridCellOutcome] = []
    started = perf_counter()
    try:
        for work_unit in work_units.plan_tiles(context, TILE_SHAPE):
            outcomes.extend(
                _execute_tasks(executor, "hybrid", work_units.tile_tasks(work_unit))
            )
        elapsed = perf_counter() - started
    finally:
        executor.shutdown(wait=True, cancel_futures=True)
    if not all(not execution._pid_alive(process_id) for process_id in identities):
        raise RuntimeError("Fallback workers did not stop cleanly.")
    return _assemble_field(samples, "hybrid", True, outcomes, elapsed)


def _status_counts(field: HybridFieldResult) -> dict[str, int]:
    return {
        status.value: int(np.sum(field.status == status.value))
        for status in EvaluationStatus
    }


def _route_counts(field: HybridFieldResult) -> dict[str, int]:
    return {
        route: int(np.sum(field.route == route))
        for route in sorted(set(field.route.ravel()))
    }


def _fallback_coordinates(field: HybridFieldResult) -> list[dict[str, object]]:
    return [
        {
            "theta2_index": item.task.theta2_index,
            "theta1_index": item.task.theta1_index,
            "theta2_degrees": item.task.theta2_degrees,
            "theta1_degrees": item.task.theta1_degrees,
        }
        for item in field.outcomes
        if item.result.route == FALLBACK_ROUTE
    ]


def _compare_hybrid_to_controls(
    fast: HybridFieldResult,
    hybrid: HybridFieldResult,
    oracle: HybridFieldResult,
) -> dict[str, object]:
    fast_errors = {
        item.task.linear_index
        for item in fast.outcomes
        if item.result.evaluation.status is EvaluationStatus.EXECUTION_ERROR
    }
    fallback_indices = {
        item.task.linear_index
        for item in hybrid.outcomes
        if item.result.route == FALLBACK_ROUTE
    }
    unexpected_changes = []
    fallback_oracle_exact = True
    fast_path_exact = True
    for fast_item, hybrid_item, oracle_item in zip(
        fast.outcomes, hybrid.outcomes, oracle.outcomes
    ):
        if not (
            fast_item.task == hybrid_item.task == oracle_item.task
        ):
            raise ValueError("Control field coordinates diverged.")
        index = fast_item.task.linear_index
        if index in fallback_indices:
            fallback_oracle_exact &= (
                hybrid_item.result.evaluation.value
                == oracle_item.result.evaluation.value
                and hybrid_item.result.evaluation.status
                is oracle_item.result.evaluation.status
                and hybrid_item.result.evaluation.diagnostics
                == oracle_item.result.evaluation.diagnostics
                and hybrid_item.result.evaluation.validity_issues
                == oracle_item.result.evaluation.validity_issues
                and hybrid_item.result.evaluation.error_type
                == oracle_item.result.evaluation.error_type
                and hybrid_item.result.evaluation.error_message
                == oracle_item.result.evaluation.error_message
            )
        else:
            fast_path_exact &= (
                hybrid_item.result.evaluation.value
                == fast_item.result.evaluation.value
                and hybrid_item.result.evaluation.status
                is fast_item.result.evaluation.status
                and hybrid_item.result.evaluation.diagnostics
                == fast_item.result.evaluation.diagnostics
                and hybrid_item.result.evaluation.validity_issues
                == fast_item.result.evaluation.validity_issues
                and hybrid_item.result.evaluation.error_type
                == fast_item.result.evaluation.error_type
                and hybrid_item.result.evaluation.error_message
                == fast_item.result.evaluation.error_message
            )
        if (
            index not in fallback_indices
            and hybrid_item.result.evaluation.status
            is not fast_item.result.evaluation.status
        ):
            unexpected_changes.append(index)
    return {
        "fallback_indices_equal_fast_error_indices": fallback_indices == fast_errors,
        "fallback_results_exactly_equal_oracle": fallback_oracle_exact,
        "fast_results_unchanged": fast_path_exact,
        "unexpected_status_change_indices": unexpected_changes,
    }


def _compare_tiled(untiled: HybridFieldResult, tiled: HybridFieldResult):
    return {
        "values_equal": bool(np.array_equal(untiled.values, tiled.values, equal_nan=True)),
        "statuses_equal": bool(np.array_equal(untiled.status, tiled.status)),
        "routes_equal": bool(np.array_equal(untiled.route, tiled.route)),
        "fallback_coordinates_equal": (
            _fallback_coordinates(untiled) == _fallback_coordinates(tiled)
        ),
        "diagnostics_equal": all(
            left.result.evaluation.diagnostics == right.result.evaluation.diagnostics
            for left, right in zip(untiled.outcomes, tiled.outcomes)
        ),
        "coordinate_tasks_equal": all(
            left.task == right.task
            for left, right in zip(untiled.outcomes, tiled.outcomes)
        ),
    }


def assess_known_cases() -> list[dict[str, object]]:
    results = []
    for case in max_step_audit.AUDIT_CASES:
        spec = max_step_audit._spec_for_case(case)
        fast = evaluate_renormalized_tangent_compiled_dop853(spec)
        hybrid = evaluate_hybrid(spec)
        oracle = evaluate_renormalized_tangent_compiled(spec)
        is_historical_failure = case.expected_promoted_status == "execution_error"
        results.append(
            {
                "case": case.name,
                "angles_degrees": [case.theta1_degrees, case.theta2_degrees],
                "historical_failure": is_historical_failure,
                "route": hybrid.route,
                "status": hybrid.evaluation.status.value,
                "evaluation_unchanged_from_fast": (
                    hybrid.evaluation.value == fast.value
                    and hybrid.evaluation.status is fast.status
                    and hybrid.evaluation.diagnostics == fast.diagnostics
                    and hybrid.evaluation.validity_issues == fast.validity_issues
                    and hybrid.evaluation.error_type == fast.error_type
                    and hybrid.evaluation.error_message == fast.error_message
                ),
                "fallback_exactly_equals_oracle": (
                    hybrid.evaluation.value == oracle.value
                    and hybrid.evaluation.status is oracle.status
                    and hybrid.evaluation.diagnostics == oracle.diagnostics
                    and hybrid.evaluation.validity_issues == oracle.validity_issues
                    and hybrid.evaluation.error_type == oracle.error_type
                    and hybrid.evaluation.error_message == oracle.error_message
                ),
                "verification": (
                    asdict(hybrid.verification)
                    if hybrid.verification is not None
                    else None
                ),
            }
        )
    return results


def assess_five_fixtures() -> list[dict[str, object]]:
    results = []
    for pair in VALIDATION_ANGLE_PAIRS_DEGREES:
        spec = validation_spec(*pair)
        fast = evaluate_renormalized_tangent_compiled_dop853(spec)
        hybrid = evaluate_hybrid(spec)
        oracle_result = max_step_audit.run_renormalized_tangent_compiled(spec)
        fast_result = max_step_audit._run_renormalized_tangent_with_rhs(
            spec,
            max_step_audit.compiled_rhs(spec.parameters),
            segment_solver=max_step_audit.TracedFortranDop853Solver(spec),
        )
        results.append(
            {
                "angles_degrees": list(pair),
                "route": hybrid.route,
                "evaluation_unchanged": (
                    hybrid.evaluation.value == fast.value
                    and hybrid.evaluation.status is fast.status
                    and hybrid.evaluation.diagnostics == fast.diagnostics
                ),
                "comparison_to_oracle": compare_results(oracle_result, fast_result),
            }
        )
    return results


def assess_failure_confinement() -> dict[str, object]:
    spec = RenormalizedTangentSpec()
    unrelated_messages = (
        "controlled ordinary scalar execution error",
        "compiled DOP853 returned a non-finite or malformed state.",
        "compiled DOP853 did not reach the requested segment endpoint: 0.2 != 0.25.",
        "compiled DOP853 failed on [0.0, 0.25] with return code -2.",
    )
    unrelated = tuple(
        ScalarEvaluation(
            status=EvaluationStatus.EXECUTION_ERROR,
            value=None,
            diagnostics=None,
            elapsed_seconds=0.0,
            evaluator=COMPILED_DOP853_EVALUATOR,
            error_type="RuntimeError",
            error_message=message,
        )
        for message in unrelated_messages
    )
    prefilter_rejected = all(
        not verify_endpoint_snap_incompatibility(item, spec).candidate_message_matched
        for item in unrelated
    )
    declared = _resolved_max_step(spec)
    lookalike = ScalarEvaluation(
        status=EvaluationStatus.EXECUTION_ERROR,
        value=None,
        diagnostics=None,
        elapsed_seconds=0.0,
        evaluator=COMPILED_DOP853_EVALUATOR,
        error_type="RuntimeError",
        error_message=(
            "compiled DOP853 exceeded the declared max_step: "
            f"{1.005 * declared} > {declared}."
        ),
    )
    lookalike_verification = verify_endpoint_snap_incompatibility(lookalike, spec)

    original_fast = globals()["evaluate_renormalized_tangent_compiled_dop853"]
    try:
        preserved = []
        for error in unrelated:
            globals()["evaluate_renormalized_tangent_compiled_dop853"] = (
                lambda _spec, retained=error: retained
            )
            preserved.append(evaluate_hybrid(spec))
        globals()["evaluate_renormalized_tangent_compiled_dop853"] = (
            lambda _spec: lookalike
        )
        preserved_lookalike = evaluate_hybrid(spec)

        def programming_error(_spec):
            raise ValueError("controlled programming error")

        globals()["evaluate_renormalized_tangent_compiled_dop853"] = programming_error
        programming_propagated = False
        try:
            evaluate_hybrid(spec)
        except ValueError as error:
            programming_propagated = str(error) == "controlled programming error"
    finally:
        globals()["evaluate_renormalized_tangent_compiled_dop853"] = original_fast
    return {
        "unrelated_errors_preserved": all(
            outcome.evaluation == expected and outcome.route == FAST_ERROR_ROUTE
            for outcome, expected in zip(preserved, unrelated)
        ),
        "ordinary_nonfinite_endpoint_and_return_code_prefilter_rejected": (
            prefilter_rejected
        ),
        "lookalike_max_step_prefilter_matched": (
            lookalike_verification.candidate_message_matched
        ),
        "lookalike_max_step_mechanics_not_verified": (
            not lookalike_verification.verified
        ),
        "lookalike_max_step_error_preserved": (
            preserved_lookalike.evaluation == lookalike
            and preserved_lookalike.route == FAST_ERROR_ROUTE
        ),
        "programming_value_error_propagated": programming_propagated,
    }


def _distribution(values: list[float]) -> dict[str, float | int]:
    array = np.asarray(values, dtype=float)
    return {
        "count": len(values),
        "median_seconds": float(np.median(array)),
        "q1_seconds": float(np.percentile(array, 25)),
        "q3_seconds": float(np.percentile(array, 75)),
        "cells_per_second_at_median": 0.0,
    }


def run_field_assessment() -> dict[str, object]:
    result: dict[str, object] = {}
    for samples in (17, 25):
        modes = ("fast", "hybrid", "solve_ivp")
        measurements = {mode: [] for mode in modes}
        first: dict[str, HybridFieldResult] = {}
        for repeat in range(BENCHMARK_REPEATS):
            offset = repeat % len(modes)
            for mode in modes[offset:] + modes[:offset]:
                field = execute_untiled(samples, mode)
                measurements[mode].append(field.elapsed_seconds)
                first.setdefault(mode, field)
        tiled = execute_tiled(samples)
        distributions = {
            mode: _distribution(values) for mode, values in measurements.items()
        }
        for distribution in distributions.values():
            distribution["cells_per_second_at_median"] = (
                samples * samples / distribution["median_seconds"]
            )
        hybrid_outcomes = first["hybrid"].outcomes
        fallback_time = sum(
            item.result.fallback_elapsed_seconds for item in hybrid_outcomes
        )
        verification_time = sum(
            item.result.verification_elapsed_seconds for item in hybrid_outcomes
        )
        result[f"{samples}x{samples}"] = {
            "cell_count": samples * samples,
            "fast_status_counts": _status_counts(first["fast"]),
            "hybrid_status_counts": _status_counts(first["hybrid"]),
            "hybrid_route_counts": _route_counts(first["hybrid"]),
            "oracle_status_counts": _status_counts(first["solve_ivp"]),
            "fallback_fraction": len(_fallback_coordinates(first["hybrid"])) / (samples * samples),
            "fallback_coordinates": _fallback_coordinates(first["hybrid"]),
            "fallback_solver_elapsed_sum_seconds": fallback_time,
            "verification_elapsed_sum_seconds": verification_time,
            "control_comparison": _compare_hybrid_to_controls(
                first["fast"], first["hybrid"], first["solve_ivp"]
            ),
            "tiled_untiled": _compare_tiled(first["hybrid"], tiled),
            "timing": distributions,
            "hybrid_speedup_over_all_solve_ivp": (
                distributions["solve_ivp"]["median_seconds"]
                / distributions["hybrid"]["median_seconds"]
            ),
            "hybrid_slowdown_over_fast": (
                distributions["hybrid"]["median_seconds"]
                / distributions["fast"]["median_seconds"]
            ),
        }
    return result


def run_assessment() -> dict[str, object]:
    known = assess_known_cases()
    fixtures = assess_five_fixtures()
    failures = assess_failure_confinement()
    fields = run_field_assessment()
    accepted = bool(
        all(
            item["route"] == (
                FALLBACK_ROUTE if item["historical_failure"] else FAST_ROUTE
            )
            and item["status"] == "completed_valid"
            and (
                item["fallback_exactly_equals_oracle"]
                if item["historical_failure"]
                else item["evaluation_unchanged_from_fast"]
            )
            for item in known
        )
        and all(item["route"] == FAST_ROUTE and item["evaluation_unchanged"] for item in fixtures)
        and all(item["comparison_to_oracle"]["accepted"] for item in fixtures)
        and failures["unrelated_errors_preserved"]
        and failures["lookalike_max_step_error_preserved"]
        and failures["programming_value_error_propagated"]
        and all(
            field["control_comparison"]["fallback_indices_equal_fast_error_indices"]
            and field["control_comparison"]["fallback_results_exactly_equal_oracle"]
            and field["control_comparison"]["fast_results_unchanged"]
            and all(field["tiled_untiled"].values())
            and field["hybrid_speedup_over_all_solve_ivp"] > 1.0
            for field in fields.values()
        )
    )
    return {
        "experiment": "verified_endpoint_max_step_fallback_boundary",
        "verdict": "ACCEPT" if accepted else "REJECT",
        "trigger": (
            "exact promoted max_step RuntimeError signature followed by an "
            "independent successful endpoint-step verification"
        ),
        "known_cases": known,
        "experiment_015_fixtures": fixtures,
        "failure_confinement": failures,
        "bounded_fields": fields,
        "accepted": accepted,
    }


def save_assessment(
    assessment: dict[str, object],
    path: Path = DEFAULT_EVIDENCE_PATH,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output:
        json.dump(assessment, output, indent=2, allow_nan=False)
        output.write("\n")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_EVIDENCE_PATH)
    arguments = parser.parse_args()
    assessment = run_assessment()
    save_assessment(assessment, arguments.output)
    return 0 if assessment["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
