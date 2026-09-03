"""Experiment 016: compare execution policies for independent scalar cells."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import multiprocessing
import os
import pickle
import platform
import resource
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from time import perf_counter
from typing import Callable, Iterable


_MODULE_IMPORT_STARTED = perf_counter()
_RUNTIME_CACHE_ROOT = Path(tempfile.gettempdir()) / "double-pendulum-chaos-cache"
_RUNTIME_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(_RUNTIME_CACHE_ROOT / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(_RUNTIME_CACHE_ROOT / "xdg"))
for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
):
    os.environ.setdefault(_thread_variable, "1")

import numba
import numpy as np
import scipy


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from development.chaos_content.prototypes.state_space_maps.src.lyapunov.compiled import (
    compiled_reference_and_tangent_rhs,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.compiled_equivalence import (
    ENERGY_DIAGNOSTIC_ABSOLUTE_TOLERANCE,
    RATE_ABSOLUTE_TOLERANCE,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.evaluation import (
    evaluate_renormalized_tangent_runner,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.compiled_dop853 import (
    COMPILED_DOP853_EVALUATOR,
    evaluate_renormalized_tangent_compiled_dop853,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.grid import (
    Theta1Theta2GridSpec,
    run_theta1_theta2_grid,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.reference import (
    RenormalizedTangentDiagnostics,
    RenormalizedTangentSpec,
)
from development.chaos_content.prototypes.state_space_maps.src.state_space_fields import (
    EvaluationStatus,
    ScalarEvaluation,
)


EXPERIMENT_NAME = "independent_cell_execution_boundary"
DEFAULT_OUTPUT_DIRECTORY = (
    Path(__file__).resolve().parents[2]
    / "outputs"
    / EXPERIMENT_NAME
    / "baseline"
)
DEFAULT_EVIDENCE_PATH = DEFAULT_OUTPUT_DIRECTORY / "summary.json"
ANGLE_MINIMUM_DEGREES = 169.0
ANGLE_MAXIMUM_DEGREES = 189.0
EQUIVALENCE_SAMPLES = 9
THROUGHPUT_SAMPLE_COUNTS = (17, 25)
EXECUTION_WIDTHS = (1, 2, 4)
THREAD_PREFLIGHT_REPEATS = 2
DEFAULT_BENCHMARK_REPEATS = 3
RESET_NORM_LIMIT = 1.0e-12


@dataclass(frozen=True)
class CellTask:
    linear_index: int
    theta2_index: int
    theta1_index: int
    theta2_degrees: float
    theta1_degrees: float


@dataclass(frozen=True)
class CellOutcome:
    task: CellTask
    evaluation: ScalarEvaluation[RenormalizedTangentDiagnostics]
    worker_pid: int
    worker_peak_rss_bytes: int


@dataclass(frozen=True)
class WorkerIdentity:
    process_id: int
    warmup_seconds: float
    peak_rss_bytes: int


_WORKER_SPEC: RenormalizedTangentSpec | None = None
_WORKER_WARMUP_SECONDS: float | None = None
_MODULE_IMPORT_SECONDS = perf_counter() - _MODULE_IMPORT_STARTED


def angle_axis_degrees(samples: int) -> tuple[float, ...]:
    if isinstance(samples, bool) or not isinstance(samples, int) or samples < 2:
        raise ValueError("samples must be an integer of at least two.")
    return tuple(
        float(value)
        for value in np.linspace(
            ANGLE_MINIMUM_DEGREES,
            ANGLE_MAXIMUM_DEGREES,
            samples,
        )
    )


def grid_tasks(samples: int) -> tuple[CellTask, ...]:
    axis = angle_axis_degrees(samples)
    return tuple(
        CellTask(
            linear_index=theta2_index * samples + theta1_index,
            theta2_index=theta2_index,
            theta1_index=theta1_index,
            theta2_degrees=theta2_degrees,
            theta1_degrees=theta1_degrees,
        )
        for theta2_index, theta2_degrees in enumerate(axis)
        for theta1_index, theta1_degrees in enumerate(axis)
    )


def specification_for_task(
    task: CellTask,
    base_spec: RenormalizedTangentSpec,
) -> RenormalizedTangentSpec:
    initial_state = replace(
        base_spec.initial_state,
        theta1=math.radians(task.theta1_degrees),
        theta2=math.radians(task.theta2_degrees),
    )
    return replace(base_spec, initial_state=initial_state)


def evaluate_cell_task(
    task: CellTask,
    base_spec: RenormalizedTangentSpec,
) -> CellOutcome:
    evaluation = evaluate_renormalized_tangent_compiled_dop853(
        specification_for_task(task, base_spec)
    )
    return CellOutcome(
        task=task,
        evaluation=evaluation,
        worker_pid=os.getpid(),
        worker_peak_rss_bytes=_peak_rss_bytes(),
    )


def _initialize_process_worker(base_spec: RenormalizedTangentSpec) -> None:
    global _WORKER_SPEC, _WORKER_WARMUP_SECONDS
    _WORKER_SPEC = base_spec
    started = perf_counter()
    evaluate_renormalized_tangent_compiled_dop853(base_spec)
    _WORKER_WARMUP_SECONDS = perf_counter() - started


def _process_cell_task(task: CellTask) -> CellOutcome:
    if _WORKER_SPEC is None:
        raise RuntimeError("Process worker was not initialized.")
    return evaluate_cell_task(task, _WORKER_SPEC)


def _process_worker_identity(delay_seconds: float = 0.02) -> WorkerIdentity:
    if _WORKER_WARMUP_SECONDS is None:
        raise RuntimeError("Process worker warm-up was not recorded.")
    time.sleep(delay_seconds)
    return WorkerIdentity(
        process_id=os.getpid(),
        warmup_seconds=_WORKER_WARMUP_SECONDS,
        peak_rss_bytes=_peak_rss_bytes(),
    )


def run_sequential(
    tasks: Iterable[CellTask],
    base_spec: RenormalizedTangentSpec,
) -> tuple[CellOutcome, ...]:
    return tuple(evaluate_cell_task(task, base_spec) for task in tasks)


def run_thread_pool(
    executor: ThreadPoolExecutor,
    tasks: Iterable[CellTask],
    base_spec: RenormalizedTangentSpec,
) -> tuple[CellOutcome, ...]:
    def evaluate(task: CellTask) -> CellOutcome:
        return evaluate_cell_task(task, base_spec)

    return tuple(executor.map(evaluate, tasks))


def run_process_pool(
    executor: ProcessPoolExecutor,
    tasks: Iterable[CellTask],
    *,
    chunksize: int,
) -> tuple[CellOutcome, ...]:
    if chunksize <= 0:
        raise ValueError("chunksize must be positive.")
    return tuple(executor.map(_process_cell_task, tasks, chunksize=chunksize))


def amortized_chunksize(cell_count: int, worker_count: int) -> int:
    if cell_count <= 0 or worker_count <= 0:
        raise ValueError("cell_count and worker_count must be positive.")
    return max(1, math.ceil(cell_count / (8 * worker_count)))


def compare_outcomes(
    baseline: Iterable[CellOutcome],
    candidate: Iterable[CellOutcome],
) -> dict[str, object]:
    baseline_items = tuple(baseline)
    candidate_items = tuple(candidate)
    baseline_by_index = _unique_outcomes_by_index(baseline_items)
    candidate_by_index = _unique_outcomes_by_index(candidate_items)
    expected_indices = set(baseline_by_index)
    candidate_indices = set(candidate_by_index)
    missing = sorted(expected_indices - candidate_indices)
    unexpected = sorted(candidate_indices - expected_indices)

    coordinate_mismatches = 0
    status_mismatches = 0
    issue_mismatches = 0
    error_mismatches = 0
    provenance_mismatches = 0
    solver_evaluation_mismatches = 0
    exact_value_matches = 0
    exact_diagnostic_matches = 0
    maximum_rate_error = 0.0
    maximum_energy_error = 0.0
    maximum_reset_norm = 0.0

    for index in sorted(expected_indices & candidate_indices):
        expected = baseline_by_index[index]
        actual = candidate_by_index[index]
        if expected.task != actual.task:
            coordinate_mismatches += 1
        expected_evaluation = expected.evaluation
        actual_evaluation = actual.evaluation
        if expected_evaluation.status is not actual_evaluation.status:
            status_mismatches += 1
        if expected_evaluation.validity_issues != actual_evaluation.validity_issues:
            issue_mismatches += 1
        if (
            expected_evaluation.error_type != actual_evaluation.error_type
            or expected_evaluation.error_message != actual_evaluation.error_message
        ):
            error_mismatches += 1
        if expected_evaluation.evaluator != actual_evaluation.evaluator:
            provenance_mismatches += 1

        if expected_evaluation.value is None or actual_evaluation.value is None:
            if expected_evaluation.value is actual_evaluation.value:
                exact_value_matches += 1
        else:
            rate_error = abs(expected_evaluation.value - actual_evaluation.value)
            maximum_rate_error = max(maximum_rate_error, rate_error)
            if expected_evaluation.value == actual_evaluation.value:
                exact_value_matches += 1

        expected_diagnostics = expected_evaluation.diagnostics
        actual_diagnostics = actual_evaluation.diagnostics
        if expected_diagnostics is None or actual_diagnostics is None:
            if expected_diagnostics is actual_diagnostics:
                exact_diagnostic_matches += 1
            continue
        energy_error = abs(
            expected_diagnostics.maximum_normalized_reference_energy_drift
            - actual_diagnostics.maximum_normalized_reference_energy_drift
        )
        maximum_energy_error = max(maximum_energy_error, energy_error)
        maximum_reset_norm = max(
            maximum_reset_norm,
            actual_diagnostics.maximum_post_renormalization_norm_error,
        )
        if (
            expected_diagnostics.segment_count != actual_diagnostics.segment_count
            or expected_diagnostics.max_step_seconds
            != actual_diagnostics.max_step_seconds
            or expected_diagnostics.numerically_valid
            != actual_diagnostics.numerically_valid
        ):
            provenance_mismatches += 1
        if (
            expected_diagnostics.solver_function_evaluations
            != actual_diagnostics.solver_function_evaluations
        ):
            solver_evaluation_mismatches += 1
        if expected_diagnostics == actual_diagnostics:
            exact_diagnostic_matches += 1

    accepted = (
        not missing
        and not unexpected
        and len(candidate_items) == len(candidate_by_index)
        and coordinate_mismatches == 0
        and status_mismatches == 0
        and issue_mismatches == 0
        and error_mismatches == 0
        and provenance_mismatches == 0
        and solver_evaluation_mismatches == 0
        and maximum_rate_error <= RATE_ABSOLUTE_TOLERANCE
        and maximum_energy_error <= ENERGY_DIAGNOSTIC_ABSOLUTE_TOLERANCE
        and maximum_reset_norm <= RESET_NORM_LIMIT
    )
    return {
        "accepted": accepted,
        "expected_cell_count": len(baseline_items),
        "candidate_cell_count": len(candidate_items),
        "missing_linear_indices": missing,
        "unexpected_linear_indices": unexpected,
        "duplicate_candidate_count": len(candidate_items) - len(candidate_by_index),
        "coordinate_mismatches": coordinate_mismatches,
        "status_mismatches": status_mismatches,
        "validity_issue_mismatches": issue_mismatches,
        "error_semantics_mismatches": error_mismatches,
        "provenance_mismatches": provenance_mismatches,
        "solver_evaluation_mismatches": solver_evaluation_mismatches,
        "exact_value_matches": exact_value_matches,
        "exact_diagnostic_matches": exact_diagnostic_matches,
        "maximum_rate_error_per_second": maximum_rate_error,
        "maximum_energy_diagnostic_error": maximum_energy_error,
        "maximum_candidate_reset_norm_error": maximum_reset_norm,
        "result_digest": outcome_digest(candidate_items),
    }


def current_grid_crosscheck(
    baseline: tuple[CellOutcome, ...],
    base_spec: RenormalizedTangentSpec,
) -> dict[str, object]:
    axis = angle_axis_degrees(EQUIVALENCE_SAMPLES)
    grid = run_theta1_theta2_grid(
        Theta1Theta2GridSpec(
            theta1_degrees=axis,
            theta2_degrees=axis,
            observable_spec=base_spec,
        ),
        evaluator=evaluate_renormalized_tangent_compiled_dop853,
    )
    converted = tuple(
        CellOutcome(
            task=CellTask(
                linear_index=cell.y_index * EQUIVALENCE_SAMPLES + cell.x_index,
                theta2_index=cell.y_index,
                theta1_index=cell.x_index,
                theta2_degrees=cell.y_coordinate,
                theta1_degrees=cell.x_coordinate,
            ),
            evaluation=cell.evaluation,
            worker_pid=os.getpid(),
            worker_peak_rss_bytes=_peak_rss_bytes(),
        )
        for row in grid.cells
        for cell in row
    )
    return compare_outcomes(baseline, converted)


def outcome_digest(outcomes: Iterable[CellOutcome]) -> str:
    records = []
    for outcome in sorted(outcomes, key=lambda item: item.task.linear_index):
        evaluation = outcome.evaluation
        diagnostics = evaluation.diagnostics
        records.append(
            {
                "task": asdict(outcome.task),
                "status": evaluation.status.value,
                "value": evaluation.value,
                "issues": list(evaluation.validity_issues),
                "error_type": evaluation.error_type,
                "error_message": evaluation.error_message,
                "energy": None
                if diagnostics is None
                else diagnostics.maximum_normalized_reference_energy_drift,
                "reset": None
                if diagnostics is None
                else diagnostics.maximum_post_renormalization_norm_error,
                "nfev": None
                if diagnostics is None
                else diagnostics.solver_function_evaluations,
            }
        )
    encoded = json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _unique_outcomes_by_index(
    outcomes: Iterable[CellOutcome],
) -> dict[int, CellOutcome]:
    result: dict[int, CellOutcome] = {}
    for outcome in outcomes:
        result.setdefault(outcome.task.linear_index, outcome)
    return result


def _runtime_error_runner(_spec: RenormalizedTangentSpec):
    raise RuntimeError("controlled numerical failure")


def controlled_outcome_probe(
    kind: str,
    base_spec: RenormalizedTangentSpec,
) -> ScalarEvaluation[RenormalizedTangentDiagnostics]:
    if kind == "completed_invalid":
        return evaluate_renormalized_tangent_compiled_dop853(
            replace(base_spec, duration=0.25, energy_drift_limit=1.0e-20)
        )
    if kind == "execution_error":
        return evaluate_renormalized_tangent_runner(
            replace(base_spec, duration=0.25),
            runner=_runtime_error_runner,
            evaluator="controlled_probe",
        )
    if kind == "programming_error":
        raise ValueError("controlled programming failure")
    raise ValueError(f"Unknown controlled probe: {kind}.")


def _process_controlled_probe(kind: str):
    if _WORKER_SPEC is None:
        raise RuntimeError("Process worker was not initialized.")
    return controlled_outcome_probe(kind, _WORKER_SPEC)


def evaluate_failure_semantics(
    process_executor: ProcessPoolExecutor | None = None,
    thread_executor: ThreadPoolExecutor | None = None,
    base_spec: RenormalizedTangentSpec | None = None,
) -> dict[str, object]:
    spec = base_spec or RenormalizedTangentSpec()

    def assess(call: Callable[[str], object]) -> dict[str, object]:
        invalid = call("completed_invalid")
        execution_error = call("execution_error")
        programming_error_propagated = False
        try:
            call("programming_error")
        except ValueError as error:
            programming_error_propagated = str(error) == "controlled programming failure"
        return {
            "completed_invalid_preserved": (
                isinstance(invalid, ScalarEvaluation)
                and invalid.status is EvaluationStatus.COMPLETED_INVALID
                and bool(invalid.validity_issues)
            ),
            "execution_error_preserved": (
                isinstance(execution_error, ScalarEvaluation)
                and execution_error.status is EvaluationStatus.EXECUTION_ERROR
                and execution_error.error_type == "RuntimeError"
                and execution_error.error_message == "controlled numerical failure"
            ),
            "programming_error_propagated": programming_error_propagated,
        }

    result = {"sequential": assess(lambda kind: controlled_outcome_probe(kind, spec))}
    if thread_executor is not None:
        result["thread"] = assess(
            lambda kind: thread_executor.submit(
                controlled_outcome_probe, kind, spec
            ).result()
        )
    if process_executor is not None:
        result["process"] = assess(
            lambda kind: process_executor.submit(_process_controlled_probe, kind).result()
        )
    for strategy, checks in result.items():
        checks["accepted"] = all(checks.values())
    return result


def _run_measurement(
    strategy: str,
    samples: int,
    width: int,
    chunksize: int | None,
    run: Callable[[], tuple[CellOutcome, ...]],
    baseline: tuple[CellOutcome, ...],
) -> dict[str, object]:
    coordinator_before = _peak_rss_bytes()
    started = perf_counter()
    outcomes = run()
    elapsed = perf_counter() - started
    coordinator_after = _peak_rss_bytes()
    comparison = compare_outcomes(baseline, outcomes)
    worker_peaks: dict[int, int] = {}
    for outcome in outcomes:
        worker_peaks[outcome.worker_pid] = max(
            worker_peaks.get(outcome.worker_pid, 0),
            outcome.worker_peak_rss_bytes,
        )
    evaluator_elapsed_sum = float(
        sum(outcome.evaluation.elapsed_seconds for outcome in outcomes)
    )
    return {
        "strategy": strategy,
        "samples_per_axis": samples,
        "cell_count": len(outcomes),
        "width": width,
        "chunksize": chunksize,
        "wall_seconds": elapsed,
        "cells_per_second": len(outcomes) / elapsed,
        "effective_seconds_per_cell": elapsed / len(outcomes),
        "evaluator_elapsed_sum_seconds": evaluator_elapsed_sum,
        "evaluator_sum_to_wall_ratio": evaluator_elapsed_sum / elapsed,
        "coordinator_peak_rss_before_bytes": coordinator_before,
        "coordinator_peak_rss_after_bytes": coordinator_after,
        "worker_peak_rss_bytes_by_pid": {
            str(pid): value for pid, value in sorted(worker_peaks.items())
        },
        "aggregate_worker_peak_rss_bytes": sum(worker_peaks.values()),
        "comparison": comparison,
    }


def _distribution(measurements: list[dict[str, object]]) -> dict[str, object]:
    wall = np.asarray([item["wall_seconds"] for item in measurements], dtype=float)
    throughput = np.asarray(
        [item["cells_per_second"] for item in measurements], dtype=float
    )
    effective = np.asarray(
        [item["effective_seconds_per_cell"] for item in measurements], dtype=float
    )
    return {
        "sample_count": len(measurements),
        "wall_seconds_median": float(np.median(wall)),
        "wall_seconds_iqr": float(np.percentile(wall, 75) - np.percentile(wall, 25)),
        "wall_seconds_q1": float(np.percentile(wall, 25)),
        "wall_seconds_q3": float(np.percentile(wall, 75)),
        "cells_per_second_median": float(np.median(throughput)),
        "cells_per_second_iqr": float(
            np.percentile(throughput, 75) - np.percentile(throughput, 25)
        ),
        "effective_seconds_per_cell_median": float(np.median(effective)),
        "all_equivalence_checks_passed": all(
            item["comparison"]["accepted"] for item in measurements
        ),
        "measurements": measurements,
    }


def _wait_for_process_workers(
    executor: ProcessPoolExecutor,
    expected_workers: int,
) -> tuple[WorkerIdentity, ...]:
    identities: dict[int, WorkerIdentity] = {}
    for _attempt in range(8):
        futures = [
            executor.submit(_process_worker_identity, 0.03)
            for _ in range(expected_workers * 3)
        ]
        for future in futures:
            identity = future.result()
            identities[identity.process_id] = identity
        if len(identities) == expected_workers:
            break
    if len(identities) != expected_workers:
        raise RuntimeError(
            f"Expected {expected_workers} initialized workers, observed "
            f"{sorted(identities)}."
        )
    return tuple(identities[pid] for pid in sorted(identities))


def _pid_alive(process_id: int) -> bool:
    try:
        os.kill(process_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def _timing_group_key(
    strategy: str, samples: int, width: int, dispatch_policy: str
) -> str:
    return f"{strategy}|{samples}x{samples}|w{width}|{dispatch_policy}"


def run_assessment(benchmark_repeats: int = DEFAULT_BENCHMARK_REPEATS) -> dict[str, object]:
    if benchmark_repeats <= 0:
        raise ValueError("benchmark_repeats must be positive.")
    base_spec = RenormalizedTangentSpec()
    logical_cpus = os.cpu_count() or 1
    widths = tuple(width for width in EXECUTION_WIDTHS if width <= logical_cpus)

    numba_was_compiled = bool(compiled_reference_and_tangent_rhs.signatures)
    cold_started = perf_counter()
    cold_outcome = evaluate_renormalized_tangent_compiled_dop853(base_spec)
    cold_seconds = perf_counter() - cold_started
    if not cold_outcome.numerically_valid:
        raise RuntimeError("Cold promoted evaluator warm-up was not numerically valid.")

    equivalence_tasks = grid_tasks(EQUIVALENCE_SAMPLES)
    baseline_started = perf_counter()
    equivalence_baseline = run_sequential(equivalence_tasks, base_spec)
    baseline_equivalence_seconds = perf_counter() - baseline_started
    grid_crosscheck = current_grid_crosscheck(equivalence_baseline, base_spec)

    benchmark_tasks = {
        samples: grid_tasks(samples) for samples in THROUGHPUT_SAMPLE_COUNTS
    }
    baseline_by_samples = {
        samples: run_sequential(tasks, base_spec)
        for samples, tasks in benchmark_tasks.items()
    }
    timing_measurements: dict[str, list[dict[str, object]]] = {}

    for repeat in range(benchmark_repeats):
        sample_order = list(THROUGHPUT_SAMPLE_COUNTS)
        if repeat % 2:
            sample_order.reverse()
        for samples in sample_order:
            tasks = benchmark_tasks[samples]
            measurement = _run_measurement(
                "sequential",
                samples,
                1,
                None,
                lambda tasks=tasks: run_sequential(tasks, base_spec),
                baseline_by_samples[samples],
            )
            key = _timing_group_key("sequential", samples, 1, "direct")
            timing_measurements.setdefault(key, []).append(measurement)

    thread_results: dict[str, object] = {}
    thread_failure_probe: dict[str, object] | None = None
    for width in tuple(width for width in widths if width > 1):
        executor_started = perf_counter()
        executor = ThreadPoolExecutor(max_workers=width)
        construction_seconds = perf_counter() - executor_started
        thread_objects = ()
        preflight_comparisons = []
        preflight_failed = False
        failure_message = None
        try:
            for _repeat in range(THREAD_PREFLIGHT_REPEATS):
                outcomes = run_thread_pool(executor, equivalence_tasks, base_spec)
                comparison = compare_outcomes(equivalence_baseline, outcomes)
                preflight_comparisons.append(comparison)
                if not comparison["accepted"]:
                    preflight_failed = True
                    break
            if not preflight_failed:
                thread_failure_probe = evaluate_failure_semantics(
                    thread_executor=executor,
                    base_spec=base_spec,
                )["thread"]
                if not thread_failure_probe["accepted"]:
                    preflight_failed = True

            if not preflight_failed:
                for repeat in range(benchmark_repeats):
                    sample_order = list(THROUGHPUT_SAMPLE_COUNTS)
                    if repeat % 2:
                        sample_order.reverse()
                    for samples in sample_order:
                        tasks = benchmark_tasks[samples]
                        baseline = baseline_by_samples[samples]
                        measurement = _run_measurement(
                            "thread",
                            samples,
                            width,
                            None,
                            lambda tasks=tasks: run_thread_pool(
                                executor, tasks, base_spec
                            ),
                            baseline,
                        )
                        key = _timing_group_key("thread", samples, width, "per_cell")
                        timing_measurements.setdefault(key, []).append(measurement)
        except BaseException as error:
            preflight_failed = True
            failure_message = f"{type(error).__name__}: {error}"
        finally:
            thread_objects = tuple(executor._threads)
            shutdown_started = perf_counter()
            executor.shutdown(wait=True, cancel_futures=True)
            shutdown_seconds = perf_counter() - shutdown_started
        thread_results[str(width)] = {
            "construction_seconds": construction_seconds,
            "shutdown_seconds": shutdown_seconds,
            "threads_stopped": all(not thread.is_alive() for thread in thread_objects),
            "preflight_passed": not preflight_failed,
            "preflight_comparisons": preflight_comparisons,
            "failure_semantics": thread_failure_probe,
            "failure_message": failure_message,
        }

    process_results: dict[str, object] = {}
    process_failure_probe: dict[str, object] | None = None
    spawn_context = multiprocessing.get_context("spawn")
    for width in widths:
        construction_started = perf_counter()
        executor = ProcessPoolExecutor(
            max_workers=width,
            mp_context=spawn_context,
            initializer=_initialize_process_worker,
            initargs=(base_spec,),
        )
        construction_seconds = perf_counter() - construction_started
        ready_started = perf_counter()
        identities = _wait_for_process_workers(executor, width)
        worker_ready_seconds = perf_counter() - ready_started
        worker_ids = tuple(identity.process_id for identity in identities)
        equivalence_comparisons = []
        lifecycle_error = None
        try:
            for chunksize in (
                1,
                amortized_chunksize(len(equivalence_tasks), width),
            ):
                outcomes = run_process_pool(
                    executor,
                    equivalence_tasks,
                    chunksize=chunksize,
                )
                equivalence_comparisons.append(
                    {
                        "chunksize": chunksize,
                        **compare_outcomes(equivalence_baseline, outcomes),
                    }
                )
            if process_failure_probe is None:
                process_failure_probe = evaluate_failure_semantics(
                    process_executor=executor,
                    base_spec=base_spec,
                )["process"]

            if all(item["accepted"] for item in equivalence_comparisons):
                for repeat in range(benchmark_repeats):
                    sample_order = list(THROUGHPUT_SAMPLE_COUNTS)
                    if repeat % 2:
                        sample_order.reverse()
                    for samples in sample_order:
                        tasks = benchmark_tasks[samples]
                        baseline = baseline_by_samples[samples]
                        chunksizes = [
                            1,
                            amortized_chunksize(len(tasks), width),
                        ]
                        if repeat % 2:
                            chunksizes.reverse()
                        for chunksize in chunksizes:
                            dispatch_policy = (
                                "per_cell" if chunksize == 1 else "amortized"
                            )
                            measurement = _run_measurement(
                                "process_spawn",
                                samples,
                                width,
                                chunksize,
                                lambda tasks=tasks, chunksize=chunksize: run_process_pool(
                                    executor, tasks, chunksize=chunksize
                                ),
                                baseline,
                            )
                            key = _timing_group_key(
                                "process_spawn", samples, width, dispatch_policy
                            )
                            timing_measurements.setdefault(key, []).append(measurement)
        except BaseException as error:
            lifecycle_error = f"{type(error).__name__}: {error}"
        finally:
            shutdown_started = perf_counter()
            executor.shutdown(wait=True, cancel_futures=True)
            shutdown_seconds = perf_counter() - shutdown_started
            time.sleep(0.05)
        process_results[str(width)] = {
            "construction_seconds": construction_seconds,
            "worker_ready_seconds": worker_ready_seconds,
            "worker_identities": [asdict(identity) for identity in identities],
            "equivalence_comparisons": equivalence_comparisons,
            "failure_message": lifecycle_error,
            "shutdown_seconds": shutdown_seconds,
            "workers_stopped": all(not _pid_alive(pid) for pid in worker_ids),
        }

    sequential_failure_probe = evaluate_failure_semantics(base_spec=base_spec)[
        "sequential"
    ]
    grouped_timings = {
        key: _distribution(values) for key, values in timing_measurements.items()
    }
    decision = decide_execution_policy(
        grouped_timings,
        thread_results,
        process_results,
        sequential_failure_probe,
        process_failure_probe,
    )

    center_task = grid_tasks(EQUIVALENCE_SAMPLES)[
        (EQUIVALENCE_SAMPLES * EQUIVALENCE_SAMPLES) // 2
    ]
    center_outcome = evaluate_cell_task(center_task, base_spec)
    return {
        "experiment": "016_independent_cell_execution_boundary",
        "question": (
            "What execution strategy should evaluate many independent initial "
            "conditions using the accepted scalar observable?"
        ),
        "decision": decision,
        "scientific_contract": {
            "base_specification": asdict(base_spec),
            "evaluator": COMPILED_DOP853_EVALUATOR,
            "array_convention": "values[theta2_index, theta1_index]",
            "domain_degrees": [ANGLE_MINIMUM_DEGREES, ANGLE_MAXIMUM_DEGREES],
            "full_periodic_domain_claimed": False,
        },
        "workloads": {
            "equivalence_samples_per_axis": EQUIVALENCE_SAMPLES,
            "throughput_samples_per_axis": list(THROUGHPUT_SAMPLE_COUNTS),
            "refinement_rule": ["9", "2*(9-1)+1", "3*(9-1)+1"],
            "benchmark_repeats": benchmark_repeats,
        },
        "environment": {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "numpy_version": np.__version__,
            "scipy_version": scipy.__version__,
            "numba_version": numba.__version__,
            "logical_cpu_count": logical_cpus,
            "tested_widths": list(widths),
            "process_start_method": "spawn",
            "thread_environment": {
                name: os.environ.get(name)
                for name in (
                    "OMP_NUM_THREADS",
                    "OPENBLAS_NUM_THREADS",
                    "MKL_NUM_THREADS",
                    "NUMEXPR_NUM_THREADS",
                    "VECLIB_MAXIMUM_THREADS",
                )
            },
            "module_import_seconds": _MODULE_IMPORT_SECONDS,
        },
        "cold_start": {
            "numba_was_compiled_before_first_evaluation": numba_was_compiled,
            "first_complete_evaluation_seconds": cold_seconds,
        },
        "serialization": {
            "center_spec_pickle_bytes": len(pickle.dumps(base_spec)),
            "center_task_pickle_bytes": len(pickle.dumps(center_task)),
            "center_outcome_pickle_bytes": len(pickle.dumps(center_outcome)),
        },
        "equivalence": {
            "sequential_task_wall_seconds": baseline_equivalence_seconds,
            "current_grid_crosscheck": grid_crosscheck,
            "thread_preflights": thread_results,
            "process_preflights": process_results,
        },
        "failure_semantics": {
            "sequential": sequential_failure_probe,
            "thread": thread_failure_probe,
            "process": process_failure_probe,
        },
        "timing_groups": grouped_timings,
        "claim_boundary": {
            "tile_contract_claimed": False,
            "persistence_claimed": False,
            "full_periodic_domain_claimed": False,
            "high_resolution_map_claimed": False,
            "prototype_policy_promoted": False,
        },
    }


def decide_execution_policy(
    timing_groups: dict[str, dict[str, object]],
    thread_results: dict[str, object],
    process_results: dict[str, object],
    sequential_failure_probe: dict[str, object],
    process_failure_probe: dict[str, object] | None,
) -> dict[str, object]:
    baseline = {
        samples: timing_groups[_timing_group_key("sequential", samples, 1, "direct")]
        for samples in THROUGHPUT_SAMPLE_COUNTS
    }
    eligible: list[dict[str, object]] = []
    for key, distribution in timing_groups.items():
        strategy, sample_label, width_label, dispatch_policy = key.split("|")
        if strategy == "sequential":
            continue
        samples = int(sample_label.split("x")[0])
        if not distribution["all_equivalence_checks_passed"]:
            continue
        if distribution["wall_seconds_q3"] >= baseline[samples]["wall_seconds_q1"]:
            continue
        eligible.append(
            {
                "key": key,
                "strategy": strategy,
                "samples": samples,
                "width": int(width_label.removeprefix("w")),
                "dispatch_policy": dispatch_policy,
                "median_wall_seconds": distribution["wall_seconds_median"],
                "median_cells_per_second": distribution["cells_per_second_median"],
                "median_speedup": (
                    baseline[samples]["wall_seconds_median"]
                    / distribution["wall_seconds_median"]
                ),
            }
        )

    candidates_by_configuration: dict[tuple[str, int, str], set[int]] = {}
    for item in eligible:
        configuration = (
            item["strategy"],
            item["width"],
            item["dispatch_policy"],
        )
        candidates_by_configuration.setdefault(configuration, set()).add(item["samples"])
    sustained = [
        configuration
        for configuration, samples in candidates_by_configuration.items()
        if samples == set(THROUGHPUT_SAMPLE_COUNTS)
    ]

    valid_sustained = []
    for strategy, width, dispatch_policy in sustained:
        if strategy == "thread":
            lifecycle_valid = bool(thread_results[str(width)]["preflight_passed"])
            failure_semantics = thread_results[str(width)]["failure_semantics"]
            failure_valid = bool(failure_semantics and failure_semantics["accepted"])
        else:
            lifecycle_valid = (
                process_results[str(width)]["failure_message"] is None
                and process_results[str(width)]["workers_stopped"]
            )
            failure_valid = bool(process_failure_probe and process_failure_probe["accepted"])
        if lifecycle_valid and failure_valid:
            valid_sustained.append((strategy, width, dispatch_policy))

    if not sequential_failure_probe["accepted"]:
        return {
            "outcome": "numerical_or_harness_invalid",
            "accepted_policy": None,
            "reason": "The sequential failure-semantics baseline failed.",
            "eligible_configurations": [],
        }
    if not valid_sustained:
        return {
            "outcome": "no_concurrency_policy_promoted",
            "accepted_policy": "sequential",
            "reason": (
                "No concurrent scalar-evaluator policy produced a sustained, "
                "spread-separated improvement on both aggregate workloads with "
                "an accepted lifecycle."
            ),
            "eligible_configurations": [],
        }

    def largest_workload_time(configuration: tuple[str, int, str]) -> float:
        strategy, width, dispatch_policy = configuration
        key = _timing_group_key(
            strategy,
            max(THROUGHPUT_SAMPLE_COUNTS),
            width,
            dispatch_policy,
        )
        return timing_groups[key]["wall_seconds_median"]

    fastest = min(valid_sustained, key=largest_workload_time)
    chosen = fastest
    simpler_equivalent_dispatch = False
    if fastest[2] == "amortized":
        per_cell = (fastest[0], fastest[1], "per_cell")
        if per_cell in valid_sustained:
            intervals_overlap = all(
                _timing_intervals_overlap(
                    timing_groups[
                        _timing_group_key(
                            fastest[0], samples, fastest[1], fastest[2]
                        )
                    ],
                    timing_groups[
                        _timing_group_key(
                            per_cell[0], samples, per_cell[1], per_cell[2]
                        )
                    ],
                )
                for samples in THROUGHPUT_SAMPLE_COUNTS
            )
            if intervals_overlap:
                chosen = per_cell
                simpler_equivalent_dispatch = True
    strategy, width, dispatch_policy = chosen
    speedups = {
        f"{samples}x{samples}": (
            baseline[samples]["wall_seconds_median"]
            / timing_groups[
                _timing_group_key(strategy, samples, width, dispatch_policy)
            ]["wall_seconds_median"]
        )
        for samples in THROUGHPUT_SAMPLE_COUNTS
    }
    return {
        "outcome": "execution_policy_accepted",
        "accepted_policy": {
            "strategy": strategy,
            "width": width,
            "dispatch_policy": dispatch_policy,
            "observed_chunksize_on_25x25": (
                amortized_chunksize(25 * 25, width)
                if dispatch_policy == "amortized"
                else 1
            ),
        },
        "reason": (
            "This configuration preserved all contracts and materially "
            "improved both workloads. Per-cell dispatch was retained because "
            "its timing spread overlapped the mechanically amortized control "
            "on both workloads."
            if simpler_equivalent_dispatch
            else "This configuration preserved all contracts and produced the "
            "lowest median wall time among candidates whose improvement was "
            "separated from sequential spread on both workloads."
        ),
        "speedups_by_workload": speedups,
        "eligible_configurations": [
            {
                "strategy": item[0],
                "width": item[1],
                "dispatch_policy": item[2],
            }
            for item in valid_sustained
        ],
    }


def _timing_intervals_overlap(
    first: dict[str, object],
    second: dict[str, object],
) -> bool:
    return bool(
        first["wall_seconds_q1"] <= second["wall_seconds_q3"]
        and second["wall_seconds_q1"] <= first["wall_seconds_q3"]
    )


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
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIRECTORY,
    )
    parser.add_argument(
        "--benchmark-repeats",
        type=int,
        default=DEFAULT_BENCHMARK_REPEATS,
    )
    arguments = parser.parse_args()
    assessment = run_assessment(arguments.benchmark_repeats)
    save_assessment(assessment, arguments.output_dir / "summary.json")
    return 0 if assessment["decision"]["outcome"] != "numerical_or_harness_invalid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
