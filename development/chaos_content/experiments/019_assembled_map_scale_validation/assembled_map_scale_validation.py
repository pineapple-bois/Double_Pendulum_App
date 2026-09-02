"""Experiment 019: compose the accepted scalar-field computation boundaries."""

from __future__ import annotations

import argparse
import json
import math
import multiprocessing
import os
import platform
import resource
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from time import perf_counter
from typing import Mapping, Sequence


_CACHE_ROOT = Path(tempfile.gettempdir()) / "double-pendulum-chaos-cache"
_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(_CACHE_ROOT / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(_CACHE_ROOT / "xdg"))
for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
):
    os.environ.setdefault(_thread_variable, "1")

import h5py
import numba
import numpy as np
import scipy


EXPERIMENT_ROOT = Path(__file__).resolve().parent
EXPERIMENT_017_ROOT = EXPERIMENT_ROOT.parent / "017_rectangular_work_unit_boundary"
EXPERIMENT_018_ROOT = EXPERIMENT_ROOT.parent / "018_hdf5_persistence_boundary"
REPOSITORY_ROOT = EXPERIMENT_ROOT.parents[3]
for _path in (
    EXPERIMENT_ROOT,
    EXPERIMENT_017_ROOT,
    EXPERIMENT_018_ROOT,
    REPOSITORY_ROOT,
):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import persistence_boundary as persistence_fixture
import rectangular_work_unit_boundary as work_units

from hdf5_field_store import (
    ORIENTATION,
    CellState,
    CompletedTile,
    DuplicateTileConflict,
    FieldDefinition,
    SimulatedInterruption,
    create_dataset,
    discover_resume_state,
    inspect_dataset,
    read_authoritative_field,
    validate_dataset,
    write_completed_tile,
)

from development.chaos_content.prototypes.lyapunov_exponents.compiled import (
    run_renormalized_tangent_compiled,
)
from development.chaos_content.prototypes.lyapunov_exponents.compiled_equivalence import (
    ENERGY_DIAGNOSTIC_ABSOLUTE_TOLERANCE,
    RATE_ABSOLUTE_TOLERANCE,
    compare_results,
)
from development.chaos_content.prototypes.lyapunov_exponents.fortran_dop853 import (
    run_renormalized_tangent_compiled_fortran,
)
from development.chaos_content.prototypes.lyapunov_exponents.hybrid import (
    HYBRID_FALLBACK_EVALUATOR,
    HYBRID_FAST_ERROR_EVALUATOR,
    HYBRID_FAST_EVALUATOR,
    evaluate_renormalized_tangent_hybrid,
)
from development.chaos_content.prototypes.lyapunov_exponents.reference import (
    RenormalizedTangentDiagnostics,
    RenormalizedTangentSpec,
)
from development.chaos_content.prototypes.state_space_fields import (
    EvaluationStatus,
    PeriodicAngularDomain,
    ScalarEvaluation,
)


EXPERIMENT_NAME = "assembled_map_scale_validation"
OUTPUT_DIRECTORY = EXPERIMENT_ROOT.parents[1] / "outputs" / EXPERIMENT_NAME
UNINTERRUPTED_PATH = OUTPUT_DIRECTORY / "uninterrupted_field.h5"
RESUMED_PATH = OUTPUT_DIRECTORY / "resumed_field.h5"
CORRUPTED_PATH = OUTPUT_DIRECTORY / "corrupted_field.h5"
FIGURE_PATH = OUTPUT_DIRECTORY / "persisted_field.png"
EVIDENCE_PATH = OUTPUT_DIRECTORY / "summary.json"

SAMPLES_PER_AXIS = 64
TILE_SHAPE = work_units.TileShape(8, 8)
PROCESS_WIDTH = 4
PROCESS_CHUNKSIZE = 1
MAXIMUM_CELLS_PER_POOL = 1024
INTERRUPT_AFTER_COMPLETED_TILES = 20
TARGET_SAMPLES_PER_AXIS = 12_000
ORACLE_AXIS_INDICES = (0, SAMPLES_PER_AXIS // 2, SAMPLES_PER_AXIS - 1)
ORACLE_CELL_INDICES = tuple(
    (theta2_index, theta1_index)
    for theta2_index in ORACLE_AXIS_INDICES
    for theta1_index in ORACLE_AXIS_INDICES
)

STATUS_CODE = {
    EvaluationStatus.COMPLETED_VALID: np.uint8(CellState.COMPLETED_VALID),
    EvaluationStatus.COMPLETED_INVALID: np.uint8(CellState.COMPLETED_INVALID),
    EvaluationStatus.EXECUTION_ERROR: np.uint8(CellState.EXECUTION_ERROR),
}
STATUS_LABEL = {
    int(CellState.COMPLETED_VALID): EvaluationStatus.COMPLETED_VALID.value,
    int(CellState.COMPLETED_INVALID): EvaluationStatus.COMPLETED_INVALID.value,
    int(CellState.EXECUTION_ERROR): EvaluationStatus.EXECUTION_ERROR.value,
}
ROUTE_CODE = {
    HYBRID_FAST_EVALUATOR: np.uint8(1),
    HYBRID_FALLBACK_EVALUATOR: np.uint8(2),
    HYBRID_FAST_ERROR_EVALUATOR: np.uint8(3),
}
ROUTE_LABEL = {int(code): label for label, code in ROUTE_CODE.items()}


@dataclass(frozen=True)
class PeriodicCellTask:
    linear_index: int
    theta2_index: int
    theta1_index: int
    theta2_radians: float
    theta1_radians: float


@dataclass(frozen=True)
class CellOutcome:
    task: PeriodicCellTask
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


def periodic_context(samples: int = SAMPLES_PER_AXIS) -> work_units.FieldContext:
    if isinstance(samples, bool) or not isinstance(samples, int) or samples <= 0:
        raise ValueError("samples must be a positive integer.")
    domain = PeriodicAngularDomain(
        theta1_samples=samples,
        theta2_samples=samples,
    )
    return work_units.FieldContext(
        theta1_axis=tuple(float(value) for value in domain.theta1_axis_radians),
        theta2_axis=tuple(float(value) for value in domain.theta2_axis_radians),
        coordinate_unit="radians",
        periodic=True,
        observable_spec=RenormalizedTangentSpec(),
        evaluator="targeted_hybrid",
    )


def field_definition(context: work_units.FieldContext) -> FieldDefinition:
    base = persistence_fixture.experiment_field_definition()
    return replace(
        base,
        theta1_axis=context.theta1_axis,
        theta2_axis=context.theta2_axis,
        observable_provenance={
            "name": "one_vector_finite_time_tangent_stretching_rate",
            "symbol": "Lambda_T^(1)",
            "definition": "sum(log(r_k)) / T",
            "authoritative_meaning": (
                "fixed-horizon finite-time tangent stretching observable; "
                "no asymptotic exponent is implied"
            ),
            "field_consumer": "full-periodic initial-angle field",
        },
        software_provenance={
            "experiment": "019_assembled_map_scale_validation",
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "numba": numba.__version__,
            "h5py": h5py.__version__,
            "hdf5": h5py.version.hdf5_version,
            "platform": platform.platform(),
            "git_head": _git_head(),
        },
    )


def tile_plan(
    context: work_units.FieldContext,
) -> tuple[work_units.TileWorkUnit, ...]:
    return work_units.plan_tiles(context, TILE_SHAPE)


def tasks_for_tile(work_unit: work_units.TileWorkUnit) -> tuple[PeriodicCellTask, ...]:
    tasks = []
    theta1_samples = work_unit.context.shape[1]
    for theta2_index in range(
        work_unit.bounds.theta2_start,
        work_unit.bounds.theta2_stop,
    ):
        for theta1_index in range(
            work_unit.bounds.theta1_start,
            work_unit.bounds.theta1_stop,
        ):
            tasks.append(
                PeriodicCellTask(
                    linear_index=theta2_index * theta1_samples + theta1_index,
                    theta2_index=theta2_index,
                    theta1_index=theta1_index,
                    theta2_radians=work_unit.context.theta2_axis[theta2_index],
                    theta1_radians=work_unit.context.theta1_axis[theta1_index],
                )
            )
    return tuple(tasks)


def specification_for_task(
    task: PeriodicCellTask,
    base_spec: RenormalizedTangentSpec,
) -> RenormalizedTangentSpec:
    return replace(
        base_spec,
        initial_state=replace(
            base_spec.initial_state,
            theta1=task.theta1_radians,
            theta2=task.theta2_radians,
            omega1=0.0,
            omega2=0.0,
        ),
    )


def _initialize_worker(base_spec: RenormalizedTangentSpec) -> None:
    global _WORKER_SPEC, _WORKER_WARMUP_SECONDS
    _WORKER_SPEC = base_spec
    started = perf_counter()
    warm = evaluate_renormalized_tangent_hybrid(base_spec)
    _WORKER_WARMUP_SECONDS = perf_counter() - started
    if warm.status is not EvaluationStatus.COMPLETED_VALID:
        raise RuntimeError("Worker hybrid-evaluator warm-up was not numerically valid.")


def _evaluate_worker(task: PeriodicCellTask) -> CellOutcome:
    if _WORKER_SPEC is None:
        raise RuntimeError("Worker was not initialized.")
    evaluation = evaluate_renormalized_tangent_hybrid(
        specification_for_task(task, _WORKER_SPEC)
    )
    return CellOutcome(
        task=task,
        evaluation=evaluation,
        worker_pid=os.getpid(),
        worker_peak_rss_bytes=_peak_rss_bytes(),
    )


def _worker_identity(delay_seconds: float = 0.03) -> WorkerIdentity:
    if _WORKER_WARMUP_SECONDS is None:
        raise RuntimeError("Worker warm-up timing is unavailable.")
    time.sleep(delay_seconds)
    return WorkerIdentity(
        process_id=os.getpid(),
        warmup_seconds=_WORKER_WARMUP_SECONDS,
        peak_rss_bytes=_peak_rss_bytes(),
    )


def _wait_for_workers(
    executor: ProcessPoolExecutor,
) -> tuple[WorkerIdentity, ...]:
    identities: dict[int, WorkerIdentity] = {}
    for _attempt in range(8):
        futures = [
            executor.submit(_worker_identity, 0.03)
            for _ in range(PROCESS_WIDTH * 3)
        ]
        for future in futures:
            identity = future.result()
            identities[identity.process_id] = identity
        if len(identities) == PROCESS_WIDTH:
            break
    if len(identities) != PROCESS_WIDTH:
        raise RuntimeError(
            f"Expected {PROCESS_WIDTH} initialized workers, observed "
            f"{sorted(identities)}."
        )
    return tuple(identities[process_id] for process_id in sorted(identities))


def _open_pool(
    spec: RenormalizedTangentSpec,
) -> tuple[ProcessPoolExecutor, tuple[WorkerIdentity, ...], float]:
    if (os.cpu_count() or 1) < PROCESS_WIDTH:
        raise RuntimeError("Experiment 019 requires four logical CPUs.")
    started = perf_counter()
    executor = ProcessPoolExecutor(
        max_workers=PROCESS_WIDTH,
        mp_context=multiprocessing.get_context("spawn"),
        initializer=_initialize_worker,
        initargs=(spec,),
    )
    identities = _wait_for_workers(executor)
    return executor, identities, perf_counter() - started


def _close_pool(
    executor: ProcessPoolExecutor,
    identities: Sequence[WorkerIdentity],
    evaluated_cells: int,
    worker_peak_by_pid: Mapping[int, int],
) -> dict[str, object]:
    process_ids = [identity.process_id for identity in identities]
    final_current = _current_rss_bytes(process_ids)
    started = perf_counter()
    executor.shutdown(wait=True, cancel_futures=True)
    shutdown_seconds = perf_counter() - started
    time.sleep(0.05)
    return {
        "process_ids": process_ids,
        "evaluated_cells": evaluated_cells,
        "worker_warmup_seconds": [identity.warmup_seconds for identity in identities],
        "ready_peak_rss_bytes": [identity.peak_rss_bytes for identity in identities],
        "final_current_rss_bytes_by_pid": final_current,
        "observed_peak_rss_bytes_by_pid": {
            str(pid): int(worker_peak_by_pid.get(pid, 0)) for pid in process_ids
        },
        "shutdown_seconds": shutdown_seconds,
        "workers_stopped": all(not _pid_alive(pid) for pid in process_ids),
    }


def _compact_tile(
    tile_index: int,
    work_unit: work_units.TileWorkUnit,
    outcomes: Sequence[CellOutcome],
    *,
    attempt: int,
    evaluation_wall_seconds: float,
) -> CompletedTile:
    expected = {task.linear_index: task for task in tasks_for_tile(work_unit)}
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
    exceptional: list[dict[str, object]] = []
    spot_diagnostics: dict[str, object] = {}
    maximum_energy_drift = 0.0
    maximum_reset_error = 0.0
    solver_evaluations = 0

    for linear_index in sorted(actual):
        outcome = actual[linear_index]
        task = expected[linear_index]
        if outcome.task != task:
            raise ValueError("A returned cell changed its coordinate association.")
        local_theta2 = task.theta2_index - work_unit.bounds.theta2_start
        local_theta1 = task.theta1_index - work_unit.bounds.theta1_start
        evaluation = outcome.evaluation
        if evaluation.evaluator not in ROUTE_CODE:
            raise ValueError(f"Unknown hybrid execution route: {evaluation.evaluator}.")
        status[local_theta2, local_theta1] = STATUS_CODE[evaluation.status]
        route[local_theta2, local_theta1] = ROUTE_CODE[evaluation.evaluator]
        if evaluation.value is not None:
            values[local_theta2, local_theta1] = evaluation.value
        if evaluation.status is not EvaluationStatus.COMPLETED_VALID:
            exceptional.append(
                {
                    "theta2_index": task.theta2_index,
                    "theta1_index": task.theta1_index,
                    "theta2_radians": task.theta2_radians,
                    "theta1_radians": task.theta1_radians,
                    "status": evaluation.status.value,
                    "execution_route": evaluation.evaluator,
                    "validity_issues": list(evaluation.validity_issues),
                    "error_type": evaluation.error_type,
                    "error_message": evaluation.error_message,
                }
            )
        diagnostics = evaluation.diagnostics
        if diagnostics is not None:
            maximum_energy_drift = max(
                maximum_energy_drift,
                diagnostics.maximum_normalized_reference_energy_drift,
            )
            maximum_reset_error = max(
                maximum_reset_error,
                diagnostics.maximum_post_renormalization_norm_error,
            )
            solver_evaluations += diagnostics.solver_function_evaluations
        if (task.theta2_index, task.theta1_index) in ORACLE_CELL_INDICES:
            spot_diagnostics[f"{task.theta2_index},{task.theta1_index}"] = {
                "value": evaluation.value,
                "status": evaluation.status.value,
                "execution_route": evaluation.evaluator,
                "validity_issues": list(evaluation.validity_issues),
                "error_type": evaluation.error_type,
                "error_message": evaluation.error_message,
                "diagnostics": asdict(diagnostics) if diagnostics is not None else None,
            }

    if np.any(status == 0) or np.any(route == 0):
        raise RuntimeError("Compaction left an unassigned work-unit cell.")
    bounds = work_unit.bounds
    return CompletedTile(
        bounds=(
            bounds.theta2_start,
            bounds.theta2_stop,
            bounds.theta1_start,
            bounds.theta1_stop,
        ),
        values=values,
        status=status,
        execution_route=route,
        attempt=attempt,
        evaluation_seconds=evaluation_wall_seconds,
        diagnostics={
            "status_counts": {
                label: int(np.count_nonzero(status == code))
                for code, label in STATUS_LABEL.items()
            },
            "route_counts": {
                label: int(np.count_nonzero(route == code))
                for code, label in ROUTE_LABEL.items()
            },
            "maximum_energy_drift": maximum_energy_drift,
            "maximum_reset_norm_error": maximum_reset_error,
            "solver_function_evaluations": solver_evaluations,
            "oracle_spot_cells": spot_diagnostics,
        },
        provenance={
            "tile_index": tile_index,
            "bounds_theta2_theta1": [
                bounds.theta2_start,
                bounds.theta2_stop,
                bounds.theta1_start,
                bounds.theta1_stop,
            ],
            "orientation": ORIENTATION,
            "scientific_specification": asdict(work_unit.context.observable_spec),
            "execution_policy": {
                "process_start_method": "spawn",
                "process_width": PROCESS_WIDTH,
                "per_cell_chunksize": PROCESS_CHUNKSIZE,
                "maximum_cells_per_pool": MAXIMUM_CELLS_PER_POOL,
            },
            "evaluator_policy": "targeted_hybrid",
        },
        exceptional_cells=tuple(exceptional),
    )


def execute_pending_tiles(
    dataset_path: Path,
    context: work_units.FieldContext,
    plan: Sequence[work_units.TileWorkUnit],
    *,
    interrupt_after_completed_tiles: int | None = None,
) -> dict[str, object]:
    resume_before = discover_resume_state(dataset_path)
    if resume_before.corrupt_tile_indices:
        raise RuntimeError("Cannot resume a dataset containing corrupt completed tiles.")
    pending = list(resume_before.pending_tile_indices)
    prior_attempts: dict[int, int] = {}
    with h5py.File(dataset_path, "r") as source:
        for tile_index in pending:
            prior_attempts[tile_index] = int(source["tiles/attempt"][tile_index])

    started = perf_counter()
    coordinator_before = _coordinator_memory()
    base_spec = context.observable_spec
    assert base_spec is not None
    executor: ProcessPoolExecutor | None = None
    identities: tuple[WorkerIdentity, ...] = ()
    cells_in_pool = 0
    pool_peak_by_pid: dict[int, int] = {}
    pool_records: list[dict[str, object]] = []
    startup_seconds = 0.0
    shutdown_seconds = 0.0
    evaluation_seconds = 0.0
    persistence_seconds = 0.0
    evaluated_cells = 0
    completed_tiles = 0
    interrupted_tile_index: int | None = None
    recycled_pools = 0

    def close_current_pool() -> None:
        nonlocal executor, identities, cells_in_pool, pool_peak_by_pid
        nonlocal shutdown_seconds
        if executor is None:
            return
        record = _close_pool(
            executor,
            identities,
            cells_in_pool,
            pool_peak_by_pid,
        )
        pool_records.append(record)
        shutdown_seconds += float(record["shutdown_seconds"])
        executor = None
        identities = ()
        cells_in_pool = 0
        pool_peak_by_pid = {}

    try:
        for position, tile_index in enumerate(pending):
            work_unit = plan[tile_index]
            tile_cell_count = work_unit.bounds.cell_count
            if executor is not None and (
                cells_in_pool + tile_cell_count > MAXIMUM_CELLS_PER_POOL
            ):
                close_current_pool()
                recycled_pools += 1
            if executor is None:
                executor, identities, pool_startup = _open_pool(base_spec)
                startup_seconds += pool_startup

            tasks = tasks_for_tile(work_unit)
            evaluation_started = perf_counter()
            outcomes = tuple(
                executor.map(_evaluate_worker, tasks, chunksize=PROCESS_CHUNKSIZE)
            )
            tile_evaluation_seconds = perf_counter() - evaluation_started
            evaluation_seconds += tile_evaluation_seconds
            evaluated_cells += len(outcomes)
            cells_in_pool += len(outcomes)
            for outcome in outcomes:
                pool_peak_by_pid[outcome.worker_pid] = max(
                    pool_peak_by_pid.get(outcome.worker_pid, 0),
                    outcome.worker_peak_rss_bytes,
                )

            attempt = max(1, prior_attempts[tile_index] + 1)
            compact = _compact_tile(
                tile_index,
                work_unit,
                outcomes,
                attempt=attempt,
                evaluation_wall_seconds=tile_evaluation_seconds,
            )
            should_interrupt = (
                interrupt_after_completed_tiles is not None
                and completed_tiles >= interrupt_after_completed_tiles
            )
            persistence_started = perf_counter()
            try:
                write_completed_tile(
                    dataset_path,
                    tile_index,
                    compact,
                    interrupt_after="payload" if should_interrupt else None,
                )
            except SimulatedInterruption:
                persistence_seconds += perf_counter() - persistence_started
                interrupted_tile_index = tile_index
                break
            persistence_seconds += perf_counter() - persistence_started
            completed_tiles += 1
            del outcomes, compact

            if position == len(pending) - 1:
                break
    finally:
        close_current_pool()

    coordinator_after = _coordinator_memory()
    resume_after = discover_resume_state(dataset_path)
    return {
        "wall_seconds": perf_counter() - started,
        "setup_seconds": startup_seconds,
        "evaluation_seconds": evaluation_seconds,
        "persistence_seconds": persistence_seconds,
        "shutdown_seconds": shutdown_seconds,
        "evaluated_cells": evaluated_cells,
        "completed_tiles_in_session": completed_tiles,
        "preexisting_completed_tiles": list(resume_before.completed_tile_indices),
        "preexisting_completed_cells": sum(
            plan[index].bounds.cell_count
            for index in resume_before.completed_tile_indices
        ),
        "pending_tiles_at_start": pending,
        "interrupted_tile_index": interrupted_tile_index,
        "interrupted": interrupted_tile_index is not None,
        "pool_count": len(pool_records),
        "recycling_events": recycled_pools,
        "all_workers_stopped": all(record["workers_stopped"] for record in pool_records),
        "pools": pool_records,
        "coordinator_before": coordinator_before,
        "coordinator_after": coordinator_after,
        "completed_tiles_after": list(resume_after.completed_tile_indices),
        "writing_tiles_after": list(resume_after.writing_tile_indices),
        "not_started_tiles_after": list(resume_after.not_started_tile_indices),
    }


def initialize_dataset(
    path: Path,
    definition: FieldDefinition,
    plan: Sequence[work_units.TileWorkUnit],
) -> float:
    started = perf_counter()
    create_dataset(path, definition, tuple(work_unit.bounds for work_unit in plan))
    return perf_counter() - started


def _field_assessment(
    path: Path,
    context: work_units.FieldContext,
    plan: Sequence[work_units.TileWorkUnit],
) -> dict[str, object]:
    validation = validate_dataset(path)
    snapshot = read_authoritative_field(path)
    expected_theta1 = np.asarray(
        [-math.pi + 2.0 * math.pi * index / context.shape[1] for index in range(context.shape[1])]
    )
    expected_theta2 = np.asarray(
        [-math.pi + 2.0 * math.pi * index / context.shape[0] for index in range(context.shape[0])]
    )
    coverage = work_units.validate_tile_plan(context, plan)
    status_counts = {
        "completed_valid": int(
            np.count_nonzero(snapshot.status == CellState.COMPLETED_VALID)
        ),
        "completed_invalid": int(
            np.count_nonzero(snapshot.status == CellState.COMPLETED_INVALID)
        ),
        "execution_error": int(
            np.count_nonzero(snapshot.status == CellState.EXECUTION_ERROR)
        ),
        "not_yet_computed": int(
            np.count_nonzero(snapshot.status == CellState.NOT_YET_COMPUTED)
        ),
    }
    route_counts = {
        label: int(np.count_nonzero(snapshot.execution_route == code))
        for code, label in ROUTE_LABEL.items()
    }
    nonvalid_locations = []
    for theta2_index, theta1_index in np.argwhere(
        snapshot.status != CellState.COMPLETED_VALID
    ):
        nonvalid_locations.append(
            {
                "theta2_index": int(theta2_index),
                "theta1_index": int(theta1_index),
                "theta2_radians": float(snapshot.theta2_axis[theta2_index]),
                "theta1_radians": float(snapshot.theta1_axis[theta1_index]),
                "status": STATUS_LABEL[int(snapshot.status[theta2_index, theta1_index])],
                "execution_route": ROUTE_LABEL[
                    int(snapshot.execution_route[theta2_index, theta1_index])
                ],
            }
        )
    error_mask = snapshot.status == CellState.EXECUTION_ERROR
    valid_mask = snapshot.status == CellState.COMPLETED_VALID
    cell_count = int(np.prod(snapshot.values.shape))
    accepted = bool(
        validation.accepted
        and snapshot.values.shape == context.shape
        and np.array_equal(snapshot.theta1_axis, expected_theta1)
        and np.array_equal(snapshot.theta2_axis, expected_theta2)
        and snapshot.theta1_axis[0] == -math.pi
        and snapshot.theta2_axis[0] == -math.pi
        and not np.any(snapshot.theta1_axis == math.pi)
        and not np.any(snapshot.theta2_axis == math.pi)
        and coverage["accepted"]
        and coverage["total_tile_cells"] == cell_count
        and coverage["maximum_coverage_count"] == 1
        and status_counts["not_yet_computed"] == 0
        and sum(status_counts.values()) == cell_count
        and np.all(np.isnan(snapshot.values[error_mask]))
        and np.all(np.isfinite(snapshot.values[valid_mask]))
        and len(validation.resume_state.completed_tile_indices) == len(plan)
        and not validation.resume_state.corrupt_tile_indices
    )
    return {
        "accepted": accepted,
        "validation_accepted": validation.accepted,
        "validation_issues": list(validation.issues),
        "shape_theta2_theta1": list(snapshot.values.shape),
        "resolution_theta1_theta2": [context.shape[1], context.shape[0]],
        "theta1_axis_exact": bool(np.array_equal(snapshot.theta1_axis, expected_theta1)),
        "theta2_axis_exact": bool(np.array_equal(snapshot.theta2_axis, expected_theta2)),
        "negative_pi_included": bool(
            snapshot.theta1_axis[0] == -math.pi
            and snapshot.theta2_axis[0] == -math.pi
        ),
        "positive_pi_excluded": bool(
            not np.any(snapshot.theta1_axis == math.pi)
            and not np.any(snapshot.theta2_axis == math.pi)
        ),
        "orientation": snapshot.metadata["orientation"],
        "coverage": coverage,
        "status_counts": status_counts,
        "route_counts": route_counts,
        "nonvalid_locations": nonvalid_locations,
        "completed_tile_count": len(validation.resume_state.completed_tile_indices),
        "tile_count": len(plan),
        "execution_error_values_all_nan": bool(np.all(np.isnan(snapshot.values[error_mask]))),
        "completed_valid_values_all_finite": bool(np.all(np.isfinite(snapshot.values[valid_mask]))),
        "finite_rate_range": [
            float(np.min(snapshot.values[valid_mask])),
            float(np.max(snapshot.values[valid_mask])),
        ],
    }


def _read_tile_json(path: Path, dataset_name: str) -> tuple[dict[str, object], ...]:
    with h5py.File(path, "r") as source:
        items = []
        for raw in source[f"tiles/{dataset_name}"]:
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            items.append(json.loads(str(raw)))
    return tuple(items)


def _spot_record(
    diagnostics: Sequence[Mapping[str, object]],
    theta2_index: int,
    theta1_index: int,
) -> Mapping[str, object]:
    key = f"{theta2_index},{theta1_index}"
    matching = [
        tile["oracle_spot_cells"][key]
        for tile in diagnostics
        if key in tile["oracle_spot_cells"]
    ]
    if len(matching) != 1:
        raise RuntimeError(f"Expected one persisted spot record for {key}.")
    return matching[0]


def oracle_spot_checks(
    path: Path,
    context: work_units.FieldContext,
) -> dict[str, object]:
    snapshot = read_authoritative_field(path)
    stored_diagnostics = _read_tile_json(path, "diagnostics_json")
    comparisons = []
    for theta2_index, theta1_index in ORACLE_CELL_INDICES:
        task = PeriodicCellTask(
            linear_index=theta2_index * context.shape[1] + theta1_index,
            theta2_index=theta2_index,
            theta1_index=theta1_index,
            theta2_radians=context.theta2_axis[theta2_index],
            theta1_radians=context.theta1_axis[theta1_index],
        )
        spec = specification_for_task(task, context.observable_spec)
        oracle = run_renormalized_tangent_compiled(spec)
        oracle_rate = oracle.finite_time_stretching_rate
        oracle_status = (
            EvaluationStatus.COMPLETED_VALID
            if oracle.diagnostics.numerically_valid
            else EvaluationStatus.COMPLETED_INVALID
        )
        persisted_status = EvaluationStatus(
            STATUS_LABEL[int(snapshot.status[theta2_index, theta1_index])]
        )
        persisted_route = ROUTE_LABEL[
            int(snapshot.execution_route[theta2_index, theta1_index])
        ]
        persisted_rate = float(snapshot.values[theta2_index, theta1_index])
        spot = _spot_record(
            stored_diagnostics,
            theta2_index,
            theta1_index,
        )
        stored_energy = float(
            spot["diagnostics"]["maximum_normalized_reference_energy_drift"]
        )
        rate_error = abs(persisted_rate - oracle_rate)
        energy_error = abs(
            stored_energy
            - oracle.diagnostics.maximum_normalized_reference_energy_drift
        )
        fast_full_comparison = None
        if persisted_route == HYBRID_FAST_EVALUATOR:
            fast = run_renormalized_tangent_compiled_fortran(spec)
            fast_full_comparison = compare_results(oracle, fast)
        independent_hybrid = evaluate_renormalized_tangent_hybrid(spec)
        comparison_accepted = bool(
            rate_error <= RATE_ABSOLUTE_TOLERANCE
            and energy_error <= ENERGY_DIAGNOSTIC_ABSOLUTE_TOLERANCE
            and persisted_status is oracle_status
            and tuple(spot["validity_issues"]) == oracle.diagnostics.validity_issues
            and float(spot["value"]) == persisted_rate
            and spot["status"] == persisted_status.value
            and spot["execution_route"] == persisted_route
            and independent_hybrid.status is persisted_status
            and independent_hybrid.value == persisted_rate
            and independent_hybrid.evaluator == persisted_route
            and independent_hybrid.validity_issues
            == tuple(spot["validity_issues"])
            and (
                fast_full_comparison is None
                or fast_full_comparison["accepted"]
            )
        )
        comparisons.append(
            {
                "theta2_index": theta2_index,
                "theta1_index": theta1_index,
                "theta2_radians": task.theta2_radians,
                "theta1_radians": task.theta1_radians,
                "persisted_route": persisted_route,
                "persisted_status": persisted_status.value,
                "persisted_rate_per_second": persisted_rate,
                "oracle_rate_per_second": oracle_rate,
                "absolute_rate_error_per_second": rate_error,
                "energy_diagnostic_absolute_error": energy_error,
                "full_fast_vs_oracle": fast_full_comparison,
                "accepted": comparison_accepted,
            }
        )
    return {
        "selection": "Cartesian product of axis indices {0, N/2, N-1}",
        "axis_indices": list(ORACLE_AXIS_INDICES),
        "cell_count": len(comparisons),
        "rate_absolute_tolerance_per_second": RATE_ABSOLUTE_TOLERANCE,
        "energy_absolute_tolerance": ENERGY_DIAGNOSTIC_ABSOLUTE_TOLERANCE,
        "all_accepted": all(item["accepted"] for item in comparisons),
        "maximum_rate_error_per_second": max(
            item["absolute_rate_error_per_second"] for item in comparisons
        ),
        "maximum_energy_diagnostic_error": max(
            item["energy_diagnostic_absolute_error"] for item in comparisons
        ),
        "comparisons": comparisons,
    }


def compare_authoritative_fields(left_path: Path, right_path: Path) -> dict[str, object]:
    left = read_authoritative_field(left_path)
    right = read_authoritative_field(right_path)
    left_diagnostics = _read_tile_json(left_path, "diagnostics_json")
    right_diagnostics = _read_tile_json(right_path, "diagnostics_json")
    left_provenance = _read_tile_json(left_path, "provenance_json")
    right_provenance = _read_tile_json(right_path, "provenance_json")
    left_exceptions = _read_tile_json(left_path, "exceptional_cells_json")
    right_exceptions = _read_tile_json(right_path, "exceptional_cells_json")
    scientific_metadata_keys = (
        "orientation",
        "coordinate_unit",
        "periodic",
        "periodic_interval",
        "resolution_theta1_theta2",
        "field_shape_theta2_theta1",
        "observable_provenance",
        "physical_parameters",
        "numerical_parameters",
        "evaluator_provenance",
    )
    metadata_equal = all(
        left.metadata[key] == right.metadata[key] for key in scientific_metadata_keys
    )
    return {
        "values_exact": bool(np.array_equal(left.values, right.values, equal_nan=True)),
        "status_exact": bool(np.array_equal(left.status, right.status)),
        "execution_route_exact": bool(
            np.array_equal(left.execution_route, right.execution_route)
        ),
        "theta1_axis_exact": bool(np.array_equal(left.theta1_axis, right.theta1_axis)),
        "theta2_axis_exact": bool(np.array_equal(left.theta2_axis, right.theta2_axis)),
        "scientific_metadata_exact": metadata_equal,
        "tile_diagnostics_exact": left_diagnostics == right_diagnostics,
        "tile_provenance_exact": left_provenance == right_provenance,
        "exceptional_cells_exact": left_exceptions == right_exceptions,
        "all_equal": bool(
            np.array_equal(left.values, right.values, equal_nan=True)
            and np.array_equal(left.status, right.status)
            and np.array_equal(left.execution_route, right.execution_route)
            and np.array_equal(left.theta1_axis, right.theta1_axis)
            and np.array_equal(left.theta2_axis, right.theta2_axis)
            and metadata_equal
            and left_diagnostics == right_diagnostics
            and left_provenance == right_provenance
            and left_exceptions == right_exceptions
        ),
    }


def integrity_and_failure_assessment(
    source_path: Path,
    corrupted_path: Path,
) -> dict[str, object]:
    if corrupted_path.exists():
        corrupted_path.unlink()
    shutil.copy2(source_path, corrupted_path)
    with h5py.File(corrupted_path, "r+") as corrupted:
        corrupted["field/values"][0, 0] += 0.5
        corrupted.flush()
    corrupted_validation = validate_dataset(corrupted_path)

    snapshot = read_authoritative_field(source_path)
    diagnostics = _read_tile_json(source_path, "diagnostics_json")[0]
    provenance = _read_tile_json(source_path, "provenance_json")[0]
    with h5py.File(source_path, "r") as source:
        bounds = tuple(int(value) for value in source["tiles/bounds"][0])
        attempt = int(source["tiles/attempt"][0])
        evaluation_seconds = float(source["tiles/evaluation_seconds"][0])
    region = np.s_[bounds[0]:bounds[1], bounds[2]:bounds[3]]
    conflicting_values = snapshot.values[region].copy()
    valid_locations = np.argwhere(
        snapshot.status[region] == CellState.COMPLETED_VALID
    )
    first_valid = tuple(int(value) for value in valid_locations[0])
    conflicting_values[first_valid] += 1.0
    conflicting_completion_rejected = False
    try:
        write_completed_tile(
            source_path,
            0,
            CompletedTile(
                bounds=bounds,
                values=conflicting_values,
                status=snapshot.status[region],
                execution_route=snapshot.execution_route[region],
                attempt=attempt,
                evaluation_seconds=evaluation_seconds,
                diagnostics=diagnostics,
                provenance=provenance,
            ),
        )
    except DuplicateTileConflict:
        conflicting_completion_rejected = True

    execution_error_mask = snapshot.status == CellState.EXECUTION_ERROR
    return {
        "corrupted_dataset_rejected": not corrupted_validation.accepted,
        "corruption_issues": list(corrupted_validation.issues),
        "corrupt_tile_indices": list(
            corrupted_validation.resume_state.corrupt_tile_indices
        ),
        "conflicting_completion_rejected": conflicting_completion_rejected,
        "execution_error_cell_count": int(np.count_nonzero(execution_error_mask)),
        "execution_error_values_all_nan": bool(
            np.all(np.isnan(snapshot.values[execution_error_mask]))
        ),
    }


def _resource_summary(
    creation_seconds: float,
    sessions: Sequence[Mapping[str, object]],
    cell_count: int,
) -> dict[str, object]:
    session_wall = sum(float(session["wall_seconds"]) for session in sessions)
    total_wall = creation_seconds + session_wall
    pools = [pool for session in sessions for pool in session["pools"]]
    current_values = [
        value
        for pool in pools
        for value in pool["final_current_rss_bytes_by_pid"].values()
    ]
    peak_values = [
        value
        for pool in pools
        for value in pool["observed_peak_rss_bytes_by_pid"].values()
    ]
    return {
        "creation_seconds": creation_seconds,
        "session_wall_seconds": session_wall,
        "total_wall_seconds": total_wall,
        "effective_cells_per_second": cell_count / total_wall,
        "effective_seconds_per_cell": total_wall / cell_count,
        "setup_seconds": sum(float(session["setup_seconds"]) for session in sessions),
        "evaluation_seconds": sum(
            float(session["evaluation_seconds"]) for session in sessions
        ),
        "persistence_seconds": sum(
            float(session["persistence_seconds"]) for session in sessions
        ),
        "shutdown_seconds": sum(
            float(session["shutdown_seconds"]) for session in sessions
        ),
        "evaluated_cells": sum(int(session["evaluated_cells"]) for session in sessions),
        "pool_count": len(pools),
        "recycling_events": sum(
            int(session["recycling_events"]) for session in sessions
        ),
        "all_workers_stopped": all(bool(session["all_workers_stopped"]) for session in sessions),
        "maximum_observed_worker_current_rss_bytes": max(current_values, default=-1),
        "maximum_observed_worker_peak_rss_bytes": max(peak_values, default=-1),
        "maximum_observed_pool_current_rss_bytes": max(
            (
                sum(pool["final_current_rss_bytes_by_pid"].values())
                for pool in pools
            ),
            default=-1,
        ),
        "coordinator_peak_rss_bytes": max(
            int(session["coordinator_after"]["peak_rss_bytes"])
            for session in sessions
        ),
        "sessions": list(sessions),
    }


def _extrapolation(
    resources: Mapping[str, object],
    dataset_bytes: int,
    persistence_seconds: float,
    tile_count: int,
) -> dict[str, object]:
    target_cells = TARGET_SAMPLES_PER_AXIS**2
    target_tiles_per_axis = math.ceil(TARGET_SAMPLES_PER_AXIS / TILE_SHAPE.theta1_cells)
    target_tile_count = target_tiles_per_axis**2
    throughput = float(resources["effective_cells_per_second"])
    compute_seconds = target_cells / throughput
    observed_bytes_per_cell = dataset_bytes / (SAMPLES_PER_AXIS**2)
    storage_projection = observed_bytes_per_cell * target_cells
    persistence_per_tile = persistence_seconds / tile_count
    return {
        "target_resolution": [TARGET_SAMPLES_PER_AXIS, TARGET_SAMPLES_PER_AXIS],
        "target_cell_count": target_cells,
        "current_tile_shape_theta2_theta1": [
            TILE_SHAPE.theta2_cells,
            TILE_SHAPE.theta1_cells,
        ],
        "projected_tile_count": target_tile_count,
        "projected_pool_lifetimes_at_1024_cells": math.ceil(
            target_cells / MAXIMUM_CELLS_PER_POOL
        ),
        "linear_wall_time_seconds_at_observed_end_to_end_throughput": compute_seconds,
        "linear_wall_time_days": compute_seconds / 86_400.0,
        "raw_authoritative_array_bytes": target_cells * (8 + 1 + 1),
        "raw_authoritative_array_gibibytes": target_cells * 10 / (1024.0**3),
        "linear_file_size_bytes_from_experiment_ratio": storage_projection,
        "linear_file_size_gibibytes_from_experiment_ratio": storage_projection
        / (1024.0**3),
        "observed_persistence_seconds_per_tile": persistence_per_tile,
        "linear_persistence_seconds_at_current_tile_count": persistence_per_tile
        * target_tile_count,
        "limitations": [
            "The timing projection assumes the 64x64 end-to-end rate scales linearly.",
            "Worker startup, filesystem flushes, HDF5 metadata, cache effects, and scheduler contention may not scale linearly.",
            "Two and a quarter million 8x8 tile records are extrapolated, not validated, and may require a separately earned production work-unit scale.",
            "Compression ratio depends on the unresolved production field and cannot be assumed constant.",
            "The observed fallback fraction is resolution- and coordinate-sample-specific and is not a production forecast.",
        ],
    }


def _git_head() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return value if sys.platform == "darwin" else value * 1024


def _current_rss_bytes(process_ids: Sequence[int]) -> dict[str, int]:
    result: dict[str, int] = {}
    for process_id in process_ids:
        try:
            completed = subprocess.run(
                ["ps", "-o", "rss=", "-p", str(process_id)],
                check=True,
                capture_output=True,
                text=True,
            )
            result[str(process_id)] = int(completed.stdout.strip()) * 1024
        except (OSError, subprocess.SubprocessError, ValueError):
            continue
    return result


def _coordinator_memory() -> dict[str, int]:
    current = _current_rss_bytes([os.getpid()]).get(str(os.getpid()), -1)
    return {"current_rss_bytes": current, "peak_rss_bytes": _peak_rss_bytes()}


def _pid_alive(process_id: int) -> bool:
    try:
        os.kill(process_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def run_experiment(output_directory: Path = OUTPUT_DIRECTORY) -> dict[str, object]:
    output_directory.mkdir(parents=True, exist_ok=True)
    uninterrupted_path = output_directory / UNINTERRUPTED_PATH.name
    resumed_path = output_directory / RESUMED_PATH.name
    corrupted_path = output_directory / CORRUPTED_PATH.name
    figure_path = output_directory / FIGURE_PATH.name
    evidence_path = output_directory / EVIDENCE_PATH.name
    for path in (
        uninterrupted_path,
        resumed_path,
        corrupted_path,
        figure_path,
        evidence_path,
    ):
        if path.exists():
            path.unlink()

    context = periodic_context()
    plan = tile_plan(context)
    definition = field_definition(context)
    coverage_preflight = work_units.validate_tile_plan(context, plan)
    if not coverage_preflight["accepted"]:
        raise RuntimeError("Accepted work-unit plan failed coverage preflight.")

    uninterrupted_creation = initialize_dataset(uninterrupted_path, definition, plan)
    uninterrupted_session = execute_pending_tiles(uninterrupted_path, context, plan)
    uninterrupted_resources = _resource_summary(
        uninterrupted_creation,
        (uninterrupted_session,),
        SAMPLES_PER_AXIS**2,
    )
    uninterrupted_assessment = _field_assessment(uninterrupted_path, context, plan)

    resumed_creation = initialize_dataset(resumed_path, definition, plan)
    interrupted_session = execute_pending_tiles(
        resumed_path,
        context,
        plan,
        interrupt_after_completed_tiles=INTERRUPT_AFTER_COMPLETED_TILES,
    )
    interrupted_resume = discover_resume_state(resumed_path)
    partial_snapshot = read_authoritative_field(resumed_path)
    interrupted_tile = interrupted_session["interrupted_tile_index"]
    assert interrupted_tile is not None
    interrupted_bounds = plan[interrupted_tile].bounds
    partial_region = np.s_[
        interrupted_bounds.theta2_start:interrupted_bounds.theta2_stop,
        interrupted_bounds.theta1_start:interrupted_bounds.theta1_stop,
    ]
    partial_tile_hidden = bool(
        np.all(np.isnan(partial_snapshot.values[partial_region]))
        and np.all(
            partial_snapshot.status[partial_region]
            == CellState.NOT_YET_COMPUTED
        )
    )
    resumed_session = execute_pending_tiles(resumed_path, context, plan)
    resumed_resources = _resource_summary(
        resumed_creation,
        (interrupted_session, resumed_session),
        SAMPLES_PER_AXIS**2,
    )
    resumed_assessment = _field_assessment(resumed_path, context, plan)
    field_comparison = compare_authoritative_fields(uninterrupted_path, resumed_path)

    oracle = oracle_spot_checks(uninterrupted_path, context)
    failure = integrity_and_failure_assessment(uninterrupted_path, corrupted_path)

    static_process = subprocess.run(
        [
            sys.executable,
            str(EXPERIMENT_018_ROOT / "hdf5_field_store.py"),
            str(uninterrupted_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    independent_inspection = json.loads(static_process.stdout)
    render_process = subprocess.run(
        [
            sys.executable,
            str(EXPERIMENT_ROOT / "render_persisted_field.py"),
            str(uninterrupted_path),
            str(figure_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    render_evidence = json.loads(render_process.stdout)

    dataset_bytes = uninterrupted_path.stat().st_size
    raw_payload_bytes = SAMPLES_PER_AXIS**2 * (8 + 1 + 1)
    storage = {
        "uninterrupted_dataset_path": str(uninterrupted_path),
        "resumed_dataset_path": str(resumed_path),
        "corrupted_dataset_path": str(corrupted_path),
        "figure_path": str(figure_path),
        "uninterrupted_file_bytes": dataset_bytes,
        "resumed_file_bytes": resumed_path.stat().st_size,
        "raw_authoritative_array_bytes": raw_payload_bytes,
        "values_bytes": SAMPLES_PER_AXIS**2 * 8,
        "status_bytes": SAMPLES_PER_AXIS**2,
        "route_bytes": SAMPLES_PER_AXIS**2,
    }
    extrapolation = _extrapolation(
        uninterrupted_resources,
        dataset_bytes,
        float(uninterrupted_resources["persistence_seconds"]),
        len(plan),
    )

    resume_evidence = {
        "interruption_after_completed_tiles": INTERRUPT_AFTER_COMPLETED_TILES,
        "interrupted_tile_index": interrupted_tile,
        "completed_tiles_discovered_after_interruption": list(
            interrupted_resume.completed_tile_indices
        ),
        "writing_tiles_discovered_after_interruption": list(
            interrupted_resume.writing_tile_indices
        ),
        "partial_tile_hidden": partial_tile_hidden,
        "completed_tiles_skipped_on_resume": resumed_session[
            "preexisting_completed_tiles"
        ],
        "completed_cells_skipped_on_resume": resumed_session[
            "preexisting_completed_cells"
        ],
        "retried_tile_index": interrupted_tile,
        "resumed_field_comparison": field_comparison,
        "uninterrupted_resources": uninterrupted_resources,
        "interrupted_and_resumed_resources": resumed_resources,
        "resume_wall_overhead_seconds": resumed_resources["total_wall_seconds"]
        - uninterrupted_resources["total_wall_seconds"],
    }
    accepted = bool(
        uninterrupted_assessment["accepted"]
        and resumed_assessment["accepted"]
        and uninterrupted_assessment["status_counts"]["not_yet_computed"] == 0
        and field_comparison["all_equal"]
        and oracle["all_accepted"]
        and interrupted_session["interrupted"]
        and interrupted_resume.completed_tile_indices
        == tuple(range(INTERRUPT_AFTER_COMPLETED_TILES))
        and interrupted_resume.writing_tile_indices == (interrupted_tile,)
        and partial_tile_hidden
        and resumed_session["preexisting_completed_cells"]
        == INTERRUPT_AFTER_COMPLETED_TILES * TILE_SHAPE.cell_count
        and validate_dataset(resumed_path).accepted
        and failure["corrupted_dataset_rejected"]
        and failure["conflicting_completion_rejected"]
        and failure["execution_error_values_all_nan"]
        and independent_inspection["accepted"]
        and render_evidence["dynamics_evaluator_imported"] is False
        and figure_path.exists()
        and uninterrupted_resources["all_workers_stopped"]
        and resumed_resources["all_workers_stopped"]
    )
    evidence = {
        "experiment": EXPERIMENT_NAME,
        "verdict": "ACCEPT" if accepted else "REJECT",
        "resolution_selection": {
            "samples_per_axis": SAMPLES_PER_AXIS,
            "cell_count": SAMPLES_PER_AXIS**2,
            "rationale": (
                "Next power-of-two periodic refinement after 32x32; exactly 64 "
                "accepted 8x8 tiles and four 1024-cell worker lifetimes."
            ),
            "selected_before_field_values": True,
        },
        "environment": definition.software_provenance,
        "pipeline": {
            "observable": definition.observable_provenance,
            "numerical_parameters": definition.numerical_parameters,
            "execution": {
                "process_start_method": "spawn",
                "process_width": PROCESS_WIDTH,
                "per_cell_chunksize": PROCESS_CHUNKSIZE,
                "maximum_cells_per_pool": MAXIMUM_CELLS_PER_POOL,
            },
            "tile_shape_theta2_theta1": [
                TILE_SHAPE.theta2_cells,
                TILE_SHAPE.theta1_cells,
            ],
            "tile_count": len(plan),
            "persistence": "HDF5 schema version 1, coordinator-side single writer",
        },
        "uninterrupted_field": uninterrupted_assessment,
        "resumed_field": resumed_assessment,
        "oracle_spot_checks": oracle,
        "resume": resume_evidence,
        "integrity_and_failure": failure,
        "independent_inspection": {
            "accepted": independent_inspection["accepted"],
            "completed_tile_count": len(
                independent_inspection["completed_tile_indices"]
            ),
            "cell_state_counts": independent_inspection["cell_state_counts"],
            "dynamics_rerun": False,
        },
        "rendering": render_evidence,
        "storage": storage,
        "resource_characterization": uninterrupted_resources,
        "high_resolution_extrapolation": extrapolation,
        "claim_boundary": {
            "full_periodic_field_validated_at_selected_resolution": accepted,
            "fallback_fraction_universal": False,
            "arbitrary_horizon_validated": False,
            "production_12000_field_ready_without_separate_authorization": False,
            "distributed_or_parallel_hdf5_writes_validated": False,
        },
    }
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    return evidence


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-directory", type=Path, default=OUTPUT_DIRECTORY)
    arguments = parser.parse_args()
    evidence = run_experiment(arguments.output_directory)
    print(
        json.dumps(
            {
                "verdict": evidence["verdict"],
                "resolution": evidence["resolution_selection"]["samples_per_axis"],
                "evidence_path": str(arguments.output_directory / EVIDENCE_PATH.name),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    _main()
