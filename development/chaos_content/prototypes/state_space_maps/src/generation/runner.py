"""Bounded process runner for authoritative two-axis scalar fields."""

from __future__ import annotations

import multiprocessing
import os
import platform
import resource
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Callable, Mapping, Sequence

for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
):
    os.environ.setdefault(_thread_variable, "1")

import numpy as np

from ..state_space_fields import (
    EvaluationStatus,
    ScalarEvaluation,
)

from .hdf5 import (
    CellState,
    CompletedTile,
    FieldDefinition,
    assert_dataset_compatible,
    create_dataset,
    discover_resume_state,
    read_tile_attempts,
    write_completed_tile,
)
from .validation import ScalarFieldValidation, validate_authoritative_field
from .work_units import (
    ScalarCellTask,
    TileShape,
    TileWorkUnit,
    plan_tiles,
    tasks_for_work_unit,
    validate_tile_plan,
)


TileDiagnostics = Callable[[Sequence[ScalarEvaluation[object]]], Mapping[str, object]]
CellEvaluator = Callable[[ScalarCellTask], ScalarEvaluation[object]]
WorkerInitializer = Callable[..., None]


@dataclass(frozen=True)
class ProcessExecutionSpec:
    """Evidence-backed execution policy for the promoted scalar-field runner."""

    process_width: int = 4
    chunksize: int = 1
    maximum_cells_per_pool: int = 2048
    start_method: str = "spawn"

    def __post_init__(self) -> None:
        if min(self.process_width, self.chunksize, self.maximum_cells_per_pool) <= 0:
            raise ValueError("Process width, chunksize, and pool limit must be positive.")
        if self.start_method != "spawn":
            raise ValueError("The promoted runner supports only spawn-isolated workers.")


def accepted_process_execution_spec() -> ProcessExecutionSpec:
    return ProcessExecutionSpec()


@dataclass(frozen=True)
class EvaluatorBinding:
    """Small spawn-safe seam between field execution and one scalar observable."""

    name: str
    evaluate_cell: CellEvaluator
    execution_routes: tuple[str, ...]
    initialize_worker: WorkerInitializer | None = None
    initializer_arguments: tuple[object, ...] = ()
    summarize_tile: TileDiagnostics | None = None

    def __post_init__(self) -> None:
        if not self.name or not self.execution_routes:
            raise ValueError("An evaluator binding needs a name and execution routes.")
        if len(set(self.execution_routes)) != len(self.execution_routes):
            raise ValueError("Execution-route labels must be unique.")


@dataclass(frozen=True)
class CellOutcome:
    task: ScalarCellTask
    evaluation: ScalarEvaluation[object]
    worker_pid: int
    worker_peak_rss_bytes: int


@dataclass(frozen=True)
class WorkerIdentity:
    process_id: int
    warmup_seconds: float
    peak_rss_bytes: int


@dataclass(frozen=True)
class FieldRunSummary:
    output_path: Path
    mode: str
    total_seconds: float
    setup_seconds: float
    evaluation_seconds: float
    persistence_seconds: float
    shutdown_seconds: float
    evaluated_cells: int
    preexisting_completed_cells: int
    completed_tiles_before: int
    pending_tiles_before: int
    completed_tiles_after: int
    pending_tiles_after: int
    pool_count: int
    recycling_events: int
    all_workers_stopped: bool
    cells_per_second: float | None
    maximum_worker_peak_rss_bytes: int
    coordinator_peak_rss_bytes: int
    artifact_bytes: int
    validation: ScalarFieldValidation


@dataclass(frozen=True)
class FieldProgress:
    """Coordinator-observed persisted progress for one create or resume run."""

    output_path: Path
    mode: str
    completed_work_units: int
    total_work_units: int
    completed_cells: int
    total_cells: int
    evaluated_work_units: int
    evaluated_cells: int
    elapsed_seconds: float


ProgressCallback = Callable[[FieldProgress], None]


_WORKER_BINDING: EvaluatorBinding | None = None
_WORKER_WARMUP_SECONDS: float | None = None


def _peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if platform.system() == "Darwin" else value * 1024


def _initialize_bound_worker(binding: EvaluatorBinding) -> None:
    global _WORKER_BINDING, _WORKER_WARMUP_SECONDS
    _WORKER_BINDING = binding
    started = perf_counter()
    if binding.initialize_worker is not None:
        binding.initialize_worker(*binding.initializer_arguments)
    _WORKER_WARMUP_SECONDS = perf_counter() - started


def _evaluate_bound_cell(task: ScalarCellTask) -> CellOutcome:
    if _WORKER_BINDING is None:
        raise RuntimeError("Scalar-field worker was not initialized.")
    evaluation = _WORKER_BINDING.evaluate_cell(task)
    if not isinstance(evaluation, ScalarEvaluation):
        raise TypeError("A scalar evaluator must return ScalarEvaluation.")
    return CellOutcome(
        task=task,
        evaluation=evaluation,
        worker_pid=os.getpid(),
        worker_peak_rss_bytes=_peak_rss_bytes(),
    )


def _worker_identity(delay_seconds: float = 0.02) -> WorkerIdentity:
    if _WORKER_WARMUP_SECONDS is None:
        raise RuntimeError("Worker initialization timing is unavailable.")
    time.sleep(delay_seconds)
    return WorkerIdentity(
        process_id=os.getpid(),
        warmup_seconds=_WORKER_WARMUP_SECONDS,
        peak_rss_bytes=_peak_rss_bytes(),
    )


def _wait_for_workers(
    executor: ProcessPoolExecutor,
    process_width: int,
) -> tuple[WorkerIdentity, ...]:
    identities: dict[int, WorkerIdentity] = {}
    for _attempt in range(8):
        futures = [
            executor.submit(_worker_identity, 0.02)
            for _ in range(process_width * 3)
        ]
        for future in futures:
            identity = future.result()
            identities[identity.process_id] = identity
        if len(identities) == process_width:
            break
    if len(identities) != process_width:
        raise RuntimeError(
            f"Expected {process_width} initialized workers, observed "
            f"{sorted(identities)}."
        )
    return tuple(identities[process_id] for process_id in sorted(identities))


def _open_pool(
    binding: EvaluatorBinding,
    execution: ProcessExecutionSpec,
) -> tuple[ProcessPoolExecutor, tuple[WorkerIdentity, ...], float]:
    if (os.cpu_count() or 1) < execution.process_width:
        raise RuntimeError(
            f"Execution requires {execution.process_width} logical CPUs."
        )
    started = perf_counter()
    executor = ProcessPoolExecutor(
        max_workers=execution.process_width,
        mp_context=multiprocessing.get_context(execution.start_method),
        initializer=_initialize_bound_worker,
        initargs=(binding,),
    )
    identities = _wait_for_workers(executor, execution.process_width)
    return executor, identities, perf_counter() - started


def _pid_alive(process_id: int) -> bool:
    try:
        os.kill(process_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _close_pool(
    executor: ProcessPoolExecutor,
    identities: Sequence[WorkerIdentity],
) -> tuple[float, bool]:
    process_ids = tuple(identity.process_id for identity in identities)
    started = perf_counter()
    executor.shutdown(wait=True, cancel_futures=True)
    elapsed = perf_counter() - started
    time.sleep(0.02)
    return elapsed, all(not _pid_alive(process_id) for process_id in process_ids)


def _route_codes(definition: FieldDefinition) -> dict[str, np.uint8]:
    return {
        label: np.uint8(code)
        for code, label in definition.route_vocabulary
        if code != 0
    }


def _compact_tile(
    work_unit: TileWorkUnit,
    outcomes: Sequence[CellOutcome],
    definition: FieldDefinition,
    binding: EvaluatorBinding,
    execution: ProcessExecutionSpec,
    *,
    attempt: int,
    evaluation_seconds: float,
) -> CompletedTile:
    expected_tasks = tasks_for_work_unit(
        work_unit,
        definition.theta1_axis,
        definition.theta2_axis,
    )
    expected = {task.linear_index: task for task in expected_tasks}
    actual: dict[int, CellOutcome] = {}
    for outcome in outcomes:
        if outcome.task.linear_index in actual:
            raise ValueError("A work unit returned a duplicate cell.")
        actual[outcome.task.linear_index] = outcome
    if set(actual) != set(expected):
        raise ValueError("A work unit did not return its exact expected coverage.")

    shape = work_unit.bounds.shape
    values = np.full(shape, np.nan, dtype="<f8")
    status = np.zeros(shape, dtype=np.uint8)
    route = np.zeros(shape, dtype=np.uint8)
    route_codes = _route_codes(definition)
    status_codes = {
        EvaluationStatus.COMPLETED_VALID: np.uint8(CellState.COMPLETED_VALID),
        EvaluationStatus.COMPLETED_INVALID: np.uint8(CellState.COMPLETED_INVALID),
        EvaluationStatus.EXECUTION_ERROR: np.uint8(CellState.EXECUTION_ERROR),
    }
    exceptional: list[dict[str, object]] = []
    evaluations: list[ScalarEvaluation[object]] = []
    worker_peaks: dict[int, int] = {}
    for linear_index in sorted(actual):
        outcome = actual[linear_index]
        task = expected[linear_index]
        if outcome.task != task:
            raise ValueError("A returned cell changed its coordinate association.")
        evaluation = outcome.evaluation
        if evaluation.evaluator not in route_codes:
            raise ValueError(f"Unknown execution route: {evaluation.evaluator}.")
        local_theta2 = task.theta2_index - work_unit.bounds.theta2_start
        local_theta1 = task.theta1_index - work_unit.bounds.theta1_start
        status[local_theta2, local_theta1] = status_codes[evaluation.status]
        route[local_theta2, local_theta1] = route_codes[evaluation.evaluator]
        if evaluation.value is not None:
            values[local_theta2, local_theta1] = evaluation.value
        if (
            evaluation.status is not EvaluationStatus.COMPLETED_VALID
            or evaluation.attempted_evaluators
        ):
            exceptional.append(
                {
                    "theta2_index": task.theta2_index,
                    "theta1_index": task.theta1_index,
                    "theta2_coordinate": task.theta2_coordinate,
                    "theta1_coordinate": task.theta1_coordinate,
                    "status": evaluation.status.value,
                    "execution_route": evaluation.evaluator,
                    "validity_issues": list(evaluation.validity_issues),
                    "error_type": evaluation.error_type,
                    "error_message": evaluation.error_message,
                    "attempted_evaluators": list(
                        evaluation.attempted_evaluators
                    ),
                    "recovery_reason": evaluation.recovery_reason,
                    "implementation_provenance": dict(
                        evaluation.implementation_provenance
                    ),
                    "attempt_provenance": dict(evaluation.attempt_provenance),
                }
            )
        evaluations.append(evaluation)
        worker_peaks[outcome.worker_pid] = max(
            worker_peaks.get(outcome.worker_pid, 0),
            outcome.worker_peak_rss_bytes,
        )

    if np.any(status == 0) or np.any(route == 0):
        raise RuntimeError("Compaction left an unassigned work-unit cell.")
    diagnostics: dict[str, object] = {
        "status_counts": {
            state.name.lower(): int(np.count_nonzero(status == state))
            for state in (
                CellState.COMPLETED_VALID,
                CellState.COMPLETED_INVALID,
                CellState.EXECUTION_ERROR,
            )
        },
        "route_counts": {
            label: int(np.count_nonzero(route == code))
            for label, code in route_codes.items()
        },
        "summed_evaluator_seconds": float(
            sum(evaluation.elapsed_seconds for evaluation in evaluations)
        ),
        "worker_peak_rss_bytes": {
            str(process_id): peak for process_id, peak in sorted(worker_peaks.items())
        },
        "attempted_evaluator_counts": {
            evaluator: sum(
                evaluator in evaluation.attempted_evaluators
                for evaluation in evaluations
            )
            for evaluator in sorted(
                {
                    evaluator
                    for evaluation in evaluations
                    for evaluator in evaluation.attempted_evaluators
                }
            )
        },
        "recovery_reason_counts": {
            reason: sum(
                evaluation.recovery_reason == reason
                for evaluation in evaluations
            )
            for reason in sorted(
                {
                    evaluation.recovery_reason
                    for evaluation in evaluations
                    if evaluation.recovery_reason is not None
                }
            )
        },
    }
    if binding.summarize_tile is not None:
        extra = dict(binding.summarize_tile(evaluations))
        if diagnostics.keys() & extra.keys():
            raise ValueError("Observable tile diagnostics replace a reserved key.")
        diagnostics.update(extra)
    return CompletedTile(
        bounds=work_unit.bounds.as_tuple,
        values=values,
        status=status,
        execution_route=route,
        attempt=attempt,
        evaluation_seconds=evaluation_seconds,
        diagnostics=diagnostics,
        provenance={
            "work_unit_index": work_unit.index,
            "bounds_theta2_theta1": list(work_unit.bounds.as_tuple),
            "evaluator_binding": binding.name,
            "execution_policy": {
                "process_start_method": execution.start_method,
                "process_width": execution.process_width,
                "per_cell_chunksize": execution.chunksize,
                "maximum_cells_per_pool": execution.maximum_cells_per_pool,
            },
        },
        exceptional_cells=tuple(exceptional),
    )


def run_scalar_field(
    output_path: Path,
    field_definition: FieldDefinition,
    evaluator_binding: EvaluatorBinding,
    *,
    execution: ProcessExecutionSpec | None = None,
    mode: str,
    progress_callback: ProgressCallback | None = None,
) -> FieldRunSummary:
    """Create or resume one authoritative scalar field using bounded workers."""

    if mode not in {"create", "resume"}:
        raise ValueError("mode must be exactly 'create' or 'resume'.")
    execution = execution or accepted_process_execution_spec()
    tile_shape = TileShape(*field_definition.nominal_tile_shape)
    work_units = plan_tiles(field_definition.field_shape, tile_shape)
    coverage = validate_tile_plan(field_definition.field_shape, work_units)
    if not coverage.accepted:
        raise ValueError("The derived work-unit plan does not cover the field once.")
    if tile_shape.cell_count > execution.maximum_cells_per_pool:
        raise ValueError("One work unit exceeds the bounded worker-pool lifetime.")
    declared_routes = {
        label for code, label in field_definition.route_vocabulary if code != 0
    }
    if declared_routes != set(evaluator_binding.execution_routes):
        raise ValueError("Evaluator routes do not match the field definition.")

    output_path = Path(output_path)
    if mode == "create":
        if output_path.exists():
            raise FileExistsError(f"Refusing to replace existing field: {output_path}")
        create_dataset(
            output_path,
            field_definition,
            tuple(unit.bounds for unit in work_units),
        )
    else:
        if not output_path.exists():
            raise FileNotFoundError(f"Cannot resume missing field: {output_path}")
        assert_dataset_compatible(
            output_path,
            field_definition,
            tuple(unit.bounds for unit in work_units),
        )

    started = perf_counter()
    resume_before = discover_resume_state(output_path)
    attempts = read_tile_attempts(output_path)
    pending = resume_before.pending_tile_indices
    completed_before = set(resume_before.completed_tile_indices)
    preexisting_cells = sum(
        work_units[index].bounds.cell_count for index in completed_before
    )
    executor: ProcessPoolExecutor | None = None
    identities: tuple[WorkerIdentity, ...] = ()
    cells_in_pool = 0
    pool_count = 0
    recycling_events = 0
    all_workers_stopped = True
    setup_seconds = 0.0
    evaluation_seconds = 0.0
    persistence_seconds = 0.0
    shutdown_seconds = 0.0
    evaluated_cells = 0
    maximum_worker_peak = 0

    def report_progress() -> None:
        if progress_callback is None:
            return
        progress_callback(
            FieldProgress(
                output_path=output_path,
                mode=mode,
                completed_work_units=(
                    len(completed_before) + evaluated_work_units
                ),
                total_work_units=len(work_units),
                completed_cells=preexisting_cells + evaluated_cells,
                total_cells=coverage.planned_cell_count,
                evaluated_work_units=evaluated_work_units,
                evaluated_cells=evaluated_cells,
                elapsed_seconds=perf_counter() - started,
            )
        )

    def close_current_pool() -> None:
        nonlocal executor, identities, cells_in_pool, shutdown_seconds
        nonlocal all_workers_stopped
        if executor is None:
            return
        elapsed, stopped = _close_pool(executor, identities)
        shutdown_seconds += elapsed
        all_workers_stopped = all_workers_stopped and stopped
        executor = None
        identities = ()
        cells_in_pool = 0

    evaluated_work_units = 0
    report_progress()
    try:
        for tile_index in pending:
            work_unit = work_units[tile_index]
            if executor is not None and (
                cells_in_pool + work_unit.bounds.cell_count
                > execution.maximum_cells_per_pool
            ):
                close_current_pool()
                recycling_events += 1
            if executor is None:
                executor, identities, startup = _open_pool(
                    evaluator_binding,
                    execution,
                )
                setup_seconds += startup
                pool_count += 1

            tasks = tasks_for_work_unit(
                work_unit,
                field_definition.theta1_axis,
                field_definition.theta2_axis,
            )
            evaluation_started = perf_counter()
            outcomes = tuple(
                executor.map(
                    _evaluate_bound_cell,
                    tasks,
                    chunksize=execution.chunksize,
                )
            )
            tile_evaluation_seconds = perf_counter() - evaluation_started
            evaluation_seconds += tile_evaluation_seconds
            evaluated_cells += len(outcomes)
            cells_in_pool += len(outcomes)
            maximum_worker_peak = max(
                maximum_worker_peak,
                *(outcome.worker_peak_rss_bytes for outcome in outcomes),
            )
            compact = _compact_tile(
                work_unit,
                outcomes,
                field_definition,
                evaluator_binding,
                execution,
                attempt=max(1, attempts[tile_index] + 1),
                evaluation_seconds=tile_evaluation_seconds,
            )
            persistence_started = perf_counter()
            write_completed_tile(output_path, tile_index, compact)
            persistence_seconds += perf_counter() - persistence_started
            evaluated_work_units += 1
            report_progress()
    finally:
        close_current_pool()

    validation = validate_authoritative_field(
        output_path,
        field_definition,
        work_units,
    )
    resume_after = discover_resume_state(output_path)
    total_seconds = perf_counter() - started
    return FieldRunSummary(
        output_path=output_path,
        mode=mode,
        total_seconds=total_seconds,
        setup_seconds=setup_seconds,
        evaluation_seconds=evaluation_seconds,
        persistence_seconds=persistence_seconds,
        shutdown_seconds=shutdown_seconds,
        evaluated_cells=evaluated_cells,
        preexisting_completed_cells=preexisting_cells,
        completed_tiles_before=len(completed_before),
        pending_tiles_before=len(pending),
        completed_tiles_after=len(resume_after.completed_tile_indices),
        pending_tiles_after=len(resume_after.pending_tile_indices),
        pool_count=pool_count,
        recycling_events=recycling_events,
        all_workers_stopped=all_workers_stopped,
        cells_per_second=(
            evaluated_cells / total_seconds if evaluated_cells else None
        ),
        maximum_worker_peak_rss_bytes=maximum_worker_peak,
        coordinator_peak_rss_bytes=_peak_rss_bytes(),
        artifact_bytes=output_path.stat().st_size,
        validation=validation,
    )
