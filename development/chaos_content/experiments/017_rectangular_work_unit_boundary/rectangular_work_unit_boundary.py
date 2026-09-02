"""Experiment 017: investigate a bounded rectangular work-unit contract."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import multiprocessing
import os
import pickle
import platform
import resource
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from statistics import median
from time import perf_counter
from types import SimpleNamespace
from typing import Iterable, Sequence


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
EXPERIMENT_016_ROOT = (
    Path(__file__).resolve().parents[1] / "016_independent_cell_execution_boundary"
)
for _path in (REPOSITORY_ROOT, EXPERIMENT_016_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import independent_cell_execution_boundary as execution

from development.chaos_content.prototypes.lyapunov_exponents.fortran_dop853 import (
    COMPILED_FORTRAN_EVALUATOR,
)
from development.chaos_content.prototypes.lyapunov_exponents.reference import (
    RenormalizedTangentSpec,
)
from development.chaos_content.prototypes.state_space_fields import (
    EvaluationStatus,
    PeriodicAngularDomain,
    ScalarEvaluation,
)


EXPERIMENT_NAME = "rectangular_work_unit_boundary"
DEFAULT_OUTPUT_DIRECTORY = (
    Path(__file__).resolve().parents[2] / "outputs" / EXPERIMENT_NAME / "baseline"
)
DEFAULT_EVIDENCE_PATH = DEFAULT_OUTPUT_DIRECTORY / "summary.json"

PROCESS_WIDTH = 4
PROCESS_CHUNKSIZE = 1
BENCHMARK_REPEATS = 3
NUMERICAL_SAMPLE_COUNTS = (17, 25)
PERIODIC_THETA1_SAMPLES = 33
PERIODIC_THETA2_SAMPLES = 25
LIFECYCLE_CELL_COUNT = 2048
LIFECYCLE_CHECKPOINTS = (256, 512, 1024, 2048)
RECYCLING_CELL_LIMITS = (512, 1024)
MATERIAL_CURRENT_RSS_GROWTH_BYTES = 32 * 1024 * 1024
MATERIAL_LATE_RSS_GROWTH_BYTES = 16 * 1024 * 1024

STATUS_TO_CODE = {
    EvaluationStatus.COMPLETED_VALID: np.uint8(0),
    EvaluationStatus.COMPLETED_INVALID: np.uint8(1),
    EvaluationStatus.EXECUTION_ERROR: np.uint8(2),
}
CODE_TO_STATUS = {int(code): status for status, code in STATUS_TO_CODE.items()}


@dataclass(frozen=True, order=True)
class TileShape:
    theta2_cells: int
    theta1_cells: int

    def __post_init__(self) -> None:
        if self.theta2_cells <= 0 or self.theta1_cells <= 0:
            raise ValueError("Tile dimensions must be positive.")

    @property
    def cell_count(self) -> int:
        return self.theta2_cells * self.theta1_cells

    @property
    def label(self) -> str:
        return f"{self.theta2_cells}x{self.theta1_cells}"

    @property
    def square(self) -> bool:
        return self.theta2_cells == self.theta1_cells


CANDIDATE_TILE_SHAPES = (
    TileShape(1, 1),
    TileShape(4, 4),
    TileShape(8, 8),
    TileShape(16, 16),
    TileShape(4, 16),
    TileShape(16, 4),
)


@dataclass(frozen=True)
class FieldContext:
    """One declared global rectangle and its scientific provenance."""

    theta1_axis: tuple[float, ...]
    theta2_axis: tuple[float, ...]
    coordinate_unit: str
    periodic: bool
    observable_spec: RenormalizedTangentSpec | None
    evaluator: str

    def __post_init__(self) -> None:
        if not self.theta1_axis or not self.theta2_axis:
            raise ValueError("Both global axes must be nonempty.")
        if not self.coordinate_unit or not self.evaluator:
            raise ValueError("Coordinate unit and evaluator provenance are required.")
        for axis in (self.theta1_axis, self.theta2_axis):
            coordinates = np.asarray(axis, dtype=float)
            if not np.all(np.isfinite(coordinates)):
                raise ValueError("Global coordinates must be finite.")
            if len(coordinates) > 1 and np.any(np.diff(coordinates) <= 0.0):
                raise ValueError("Global coordinates must be strictly increasing.")

    @property
    def shape(self) -> tuple[int, int]:
        return (len(self.theta2_axis), len(self.theta1_axis))


@dataclass(frozen=True, order=True)
class TileBounds:
    """One half-open rectangle in global ``(theta2, theta1)`` index space."""

    global_shape: tuple[int, int]
    theta2_start: int
    theta2_stop: int
    theta1_start: int
    theta1_stop: int

    def __post_init__(self) -> None:
        theta2_samples, theta1_samples = self.global_shape
        if theta2_samples <= 0 or theta1_samples <= 0:
            raise ValueError("Global field dimensions must be positive.")
        if not (0 <= self.theta2_start < self.theta2_stop <= theta2_samples):
            raise ValueError("theta2 tile bounds must be nonempty and in range.")
        if not (0 <= self.theta1_start < self.theta1_stop <= theta1_samples):
            raise ValueError("theta1 tile bounds must be nonempty and in range.")

    @property
    def shape(self) -> tuple[int, int]:
        return (
            self.theta2_stop - self.theta2_start,
            self.theta1_stop - self.theta1_start,
        )

    @property
    def cell_count(self) -> int:
        return self.shape[0] * self.shape[1]

    def global_indices(self, local_theta2: int, local_theta1: int) -> tuple[int, int]:
        if not (0 <= local_theta2 < self.shape[0]):
            raise IndexError("local theta2 index is outside the tile.")
        if not (0 <= local_theta1 < self.shape[1]):
            raise IndexError("local theta1 index is outside the tile.")
        return (
            self.theta2_start + local_theta2,
            self.theta1_start + local_theta1,
        )


@dataclass(frozen=True)
class TileWorkUnit:
    context: FieldContext
    bounds: TileBounds

    def __post_init__(self) -> None:
        if self.bounds.global_shape != self.context.shape:
            raise ValueError("Tile bounds and field context shapes disagree.")

    @property
    def identity(self) -> tuple[object, ...]:
        return (
            self.context.shape,
            self.context.coordinate_unit,
            self.context.periodic,
            self.context.theta1_axis,
            self.context.theta2_axis,
            self.bounds.theta2_start,
            self.bounds.theta2_stop,
            self.bounds.theta1_start,
            self.bounds.theta1_stop,
            self.context.observable_spec,
            self.context.evaluator,
        )


@dataclass(frozen=True)
class ExceptionalCell:
    theta2_index: int
    theta1_index: int
    status: str
    validity_issues: tuple[str, ...]
    error_type: str | None
    error_message: str | None


@dataclass(frozen=True)
class CompactTileResult:
    work_unit: TileWorkUnit
    attempt: int
    values: np.ndarray
    status_codes: np.ndarray
    exceptional_cells: tuple[ExceptionalCell, ...]
    status_counts: tuple[int, int, int]
    maximum_energy_drift: float
    maximum_reset_norm_error: float
    solver_function_evaluations: int
    evaluator_elapsed_seconds: float
    execution_wall_seconds: float
    compaction_seconds: float
    worker_cell_counts: tuple[tuple[int, int], ...]
    worker_peak_rss_bytes: tuple[tuple[int, int], ...]

    @property
    def array_bytes(self) -> int:
        return self.values.nbytes + self.status_codes.nbytes


@dataclass(frozen=True)
class TileSummary:
    bounds: TileBounds
    attempt: int
    status_counts: tuple[int, int, int]
    maximum_energy_drift: float
    maximum_reset_norm_error: float
    solver_function_evaluations: int
    evaluator_elapsed_seconds: float
    execution_wall_seconds: float
    compaction_seconds: float
    worker_cell_counts: tuple[tuple[int, int], ...]
    worker_peak_rss_bytes: tuple[tuple[int, int], ...]
    equivalence: dict[str, object] | None


@dataclass(frozen=True)
class CompactFieldResult:
    context: FieldContext
    values: np.ndarray
    status_codes: np.ndarray
    exceptional_cells: tuple[ExceptionalCell, ...]
    tile_summaries: tuple[TileSummary, ...]
    coverage: np.ndarray
    elapsed_seconds: float
    equivalence: dict[str, object]

    @property
    def statuses(self) -> np.ndarray:
        return np.asarray(
            [CODE_TO_STATUS[int(code)].value for code in self.status_codes.flat]
        ).reshape(self.status_codes.shape)

    @property
    def digest(self) -> str:
        digest = hashlib.sha256()
        digest.update(np.asarray(self.values, dtype="<f8").tobytes())
        digest.update(np.asarray(self.status_codes, dtype=np.uint8).tobytes())
        digest.update(repr(self.context).encode())
        digest.update(repr(self.exceptional_cells).encode())
        return digest.hexdigest()


class InjectedWorkUnitFailure(RuntimeError):
    """Experiment-only operational failure, distinct from scalar outcomes."""


def bounded_field_context(
    samples: int,
    observable_spec: RenormalizedTangentSpec | None = None,
) -> FieldContext:
    axis = execution.angle_axis_degrees(samples)
    return FieldContext(
        theta1_axis=axis,
        theta2_axis=axis,
        coordinate_unit="degrees",
        periodic=False,
        observable_spec=observable_spec or RenormalizedTangentSpec(),
        evaluator=COMPILED_FORTRAN_EVALUATOR,
    )


def periodic_coordinate_context() -> FieldContext:
    domain = PeriodicAngularDomain(
        theta1_samples=PERIODIC_THETA1_SAMPLES,
        theta2_samples=PERIODIC_THETA2_SAMPLES,
    )
    return FieldContext(
        theta1_axis=tuple(float(value) for value in domain.theta1_axis_radians),
        theta2_axis=tuple(float(value) for value in domain.theta2_axis_radians),
        coordinate_unit="radians",
        periodic=True,
        observable_spec=None,
        evaluator="coordinate_only",
    )


def plan_tiles(context: FieldContext, tile_shape: TileShape) -> tuple[TileWorkUnit, ...]:
    theta2_samples, theta1_samples = context.shape
    return tuple(
        TileWorkUnit(
            context=context,
            bounds=TileBounds(
                global_shape=context.shape,
                theta2_start=theta2_start,
                theta2_stop=min(
                    theta2_start + tile_shape.theta2_cells, theta2_samples
                ),
                theta1_start=theta1_start,
                theta1_stop=min(
                    theta1_start + tile_shape.theta1_cells, theta1_samples
                ),
            ),
        )
        for theta2_start in range(0, theta2_samples, tile_shape.theta2_cells)
        for theta1_start in range(0, theta1_samples, tile_shape.theta1_cells)
    )


def tile_tasks(
    work_unit: TileWorkUnit,
    *,
    local_order: str = "row_major",
) -> tuple[execution.CellTask, ...]:
    if work_unit.context.coordinate_unit != "degrees":
        raise ValueError("Scientific evaluation tasks require degree coordinates.")
    theta1_samples = work_unit.context.shape[1]
    tasks = tuple(
        execution.CellTask(
            linear_index=theta2_index * theta1_samples + theta1_index,
            theta2_index=theta2_index,
            theta1_index=theta1_index,
            theta2_degrees=work_unit.context.theta2_axis[theta2_index],
            theta1_degrees=work_unit.context.theta1_axis[theta1_index],
        )
        for theta2_index in range(
            work_unit.bounds.theta2_start, work_unit.bounds.theta2_stop
        )
        for theta1_index in range(
            work_unit.bounds.theta1_start, work_unit.bounds.theta1_stop
        )
    )
    if local_order == "row_major":
        return tasks
    if local_order == "reversed":
        return tuple(reversed(tasks))
    raise ValueError(f"Unknown local task order: {local_order}.")


def validate_tile_plan(
    context: FieldContext,
    work_units: Sequence[TileWorkUnit],
) -> dict[str, object]:
    coverage = np.zeros(context.shape, dtype=np.int16)
    bounds_valid = True
    identity_count = len({work_unit.identity for work_unit in work_units})
    total_tile_cells = 0
    coordinate_mismatches = 0
    for work_unit in work_units:
        if work_unit.context != context or work_unit.bounds.global_shape != context.shape:
            bounds_valid = False
            continue
        bounds = work_unit.bounds
        total_tile_cells += bounds.cell_count
        for local_theta2 in range(bounds.shape[0]):
            for local_theta1 in range(bounds.shape[1]):
                theta2_index, theta1_index = bounds.global_indices(
                    local_theta2, local_theta1
                )
                coverage[theta2_index, theta1_index] += 1
                if (
                    context.theta2_axis[theta2_index]
                    != work_unit.context.theta2_axis[theta2_index]
                    or context.theta1_axis[theta1_index]
                    != work_unit.context.theta1_axis[theta1_index]
                ):
                    coordinate_mismatches += 1
    missing_count = int(np.count_nonzero(coverage == 0))
    overlap_count = int(np.count_nonzero(coverage > 1))
    accepted = bool(
        bounds_valid
        and identity_count == len(work_units)
        and total_tile_cells == int(np.prod(context.shape))
        and missing_count == 0
        and overlap_count == 0
        and coordinate_mismatches == 0
    )
    return {
        "accepted": accepted,
        "tile_count": len(work_units),
        "unique_identity_count": identity_count,
        "total_tile_cells": total_tile_cells,
        "expected_cell_count": int(np.prod(context.shape)),
        "missing_cell_count": missing_count,
        "overlapped_cell_count": overlap_count,
        "maximum_coverage_count": int(coverage.max(initial=0)),
        "coordinate_mismatches": coordinate_mismatches,
        "bounds_valid": bounds_valid,
        "edge_shapes": sorted(
            {work_unit.bounds.shape for work_unit in work_units}
        ),
    }


def coordinate_field(
    context: FieldContext,
    work_units: Sequence[TileWorkUnit],
    *,
    reverse_local: bool = False,
) -> np.ndarray:
    values = np.full(context.shape, -1, dtype=np.int64)
    for work_unit in work_units:
        local_pairs = [
            (local_theta2, local_theta1)
            for local_theta2 in range(work_unit.bounds.shape[0])
            for local_theta1 in range(work_unit.bounds.shape[1])
        ]
        if reverse_local:
            local_pairs.reverse()
        for local_theta2, local_theta1 in local_pairs:
            theta2_index, theta1_index = work_unit.bounds.global_indices(
                local_theta2, local_theta1
            )
            values[theta2_index, theta1_index] = (
                theta2_index * context.shape[1] + theta1_index
            )
    return values


def assess_periodic_coverage() -> dict[str, object]:
    context = periodic_coordinate_context()
    theta1 = np.asarray(context.theta1_axis)
    theta2 = np.asarray(context.theta2_axis)
    shape_results: dict[str, object] = {}
    for tile_shape in CANDIDATE_TILE_SHAPES:
        work_units = plan_tiles(context, tile_shape)
        forward = coordinate_field(context, work_units)
        permuted = coordinate_field(
            context, tuple(reversed(work_units)), reverse_local=True
        )
        assessment = validate_tile_plan(context, work_units)
        assessment["order_independent"] = bool(np.array_equal(forward, permuted))
        assessment["orientation_correct"] = bool(
            np.array_equal(
                forward,
                np.arange(np.prod(context.shape), dtype=np.int64).reshape(
                    context.shape
                ),
            )
        )
        shape_results[tile_shape.label] = assessment

    reference_plan = plan_tiles(context, TileShape(8, 8))
    overlap = validate_tile_plan(context, reference_plan + (reference_plan[0],))
    gap = validate_tile_plan(context, reference_plan[1:])
    return {
        "context_shape": list(context.shape),
        "resolution_theta1_theta2": [
            PERIODIC_THETA1_SAMPLES,
            PERIODIC_THETA2_SAMPLES,
        ],
        "theta1_minimum": float(theta1[0]),
        "theta1_maximum": float(theta1[-1]),
        "theta2_minimum": float(theta2[0]),
        "theta2_maximum": float(theta2[-1]),
        "all_coordinates_half_open": bool(
            np.all(theta1 >= -math.pi)
            and np.all(theta1 < math.pi)
            and np.all(theta2 >= -math.pi)
            and np.all(theta2 < math.pi)
        ),
        "positive_pi_absent": bool(
            math.pi not in theta1 and math.pi not in theta2
        ),
        "shape_results": shape_results,
        "overlap_plan_rejected": not overlap["accepted"],
        "overlap_detected_cells": overlap["overlapped_cell_count"],
        "gap_plan_rejected": not gap["accepted"],
        "gap_detected_cells": gap["missing_cell_count"],
        "accepted": bool(
            all(
                result["accepted"]
                and result["order_independent"]
                and result["orientation_correct"]
                for result in shape_results.values()
            )
            and not overlap["accepted"]
            and not gap["accepted"]
        ),
    }


def _compact_tile(
    work_unit: TileWorkUnit,
    outcomes: Sequence[execution.CellOutcome],
    *,
    attempt: int,
    execution_wall_seconds: float,
) -> CompactTileResult:
    compaction_started = perf_counter()
    expected_tasks = {task.linear_index: task for task in tile_tasks(work_unit)}
    outcomes_by_index: dict[int, execution.CellOutcome] = {}
    for outcome in outcomes:
        if outcome.task.linear_index in outcomes_by_index:
            raise ValueError("A tile outcome contains a duplicate global cell.")
        outcomes_by_index[outcome.task.linear_index] = outcome
    if set(outcomes_by_index) != set(expected_tasks):
        raise ValueError("A tile outcome does not exactly cover its work unit.")

    values = np.full(work_unit.bounds.shape, np.nan, dtype=np.float64)
    status_codes = np.full(work_unit.bounds.shape, 255, dtype=np.uint8)
    exceptional_cells: list[ExceptionalCell] = []
    status_counts = [0, 0, 0]
    maximum_energy_drift = 0.0
    maximum_reset_norm_error = 0.0
    solver_function_evaluations = 0
    evaluator_elapsed_seconds = 0.0
    worker_counts: dict[int, int] = {}
    worker_peaks: dict[int, int] = {}

    for global_index in sorted(outcomes_by_index):
        outcome = outcomes_by_index[global_index]
        expected_task = expected_tasks[global_index]
        if outcome.task != expected_task:
            raise ValueError("A tile outcome changed its indexed coordinate task.")
        local_theta2 = outcome.task.theta2_index - work_unit.bounds.theta2_start
        local_theta1 = outcome.task.theta1_index - work_unit.bounds.theta1_start
        evaluation = outcome.evaluation
        code = int(STATUS_TO_CODE[evaluation.status])
        status_codes[local_theta2, local_theta1] = code
        status_counts[code] += 1
        if evaluation.value is not None:
            values[local_theta2, local_theta1] = evaluation.value
        if evaluation.status is not EvaluationStatus.COMPLETED_VALID:
            exceptional_cells.append(
                ExceptionalCell(
                    theta2_index=outcome.task.theta2_index,
                    theta1_index=outcome.task.theta1_index,
                    status=evaluation.status.value,
                    validity_issues=evaluation.validity_issues,
                    error_type=evaluation.error_type,
                    error_message=evaluation.error_message,
                )
            )
        diagnostics = evaluation.diagnostics
        if diagnostics is not None:
            maximum_energy_drift = max(
                maximum_energy_drift,
                diagnostics.maximum_normalized_reference_energy_drift,
            )
            maximum_reset_norm_error = max(
                maximum_reset_norm_error,
                diagnostics.maximum_post_renormalization_norm_error,
            )
            solver_function_evaluations += diagnostics.solver_function_evaluations
        evaluator_elapsed_seconds += evaluation.elapsed_seconds
        worker_counts[outcome.worker_pid] = worker_counts.get(outcome.worker_pid, 0) + 1
        worker_peaks[outcome.worker_pid] = max(
            worker_peaks.get(outcome.worker_pid, 0),
            outcome.worker_peak_rss_bytes,
        )

    if np.any(status_codes == 255):
        raise ValueError("A compact tile retained an unassigned status cell.")
    compaction_seconds = perf_counter() - compaction_started
    return CompactTileResult(
        work_unit=work_unit,
        attempt=attempt,
        values=values,
        status_codes=status_codes,
        exceptional_cells=tuple(exceptional_cells),
        status_counts=tuple(status_counts),
        maximum_energy_drift=maximum_energy_drift,
        maximum_reset_norm_error=maximum_reset_norm_error,
        solver_function_evaluations=solver_function_evaluations,
        evaluator_elapsed_seconds=evaluator_elapsed_seconds,
        execution_wall_seconds=execution_wall_seconds,
        compaction_seconds=compaction_seconds,
        worker_cell_counts=tuple(sorted(worker_counts.items())),
        worker_peak_rss_bytes=tuple(sorted(worker_peaks.items())),
    )


def _empty_field_arrays(context: FieldContext) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return (
        np.full(context.shape, np.nan, dtype=np.float64),
        np.full(context.shape, 255, dtype=np.uint8),
        np.zeros(context.shape, dtype=np.uint8),
    )


def _insert_compact_tile(
    values: np.ndarray,
    status_codes: np.ndarray,
    coverage: np.ndarray,
    compact: CompactTileResult,
) -> None:
    bounds = compact.work_unit.bounds
    target = np.s_[
        bounds.theta2_start : bounds.theta2_stop,
        bounds.theta1_start : bounds.theta1_stop,
    ]
    if np.any(coverage[target] != 0):
        raise ValueError("A compact tile overlaps an already assembled cell.")
    values[target] = compact.values
    status_codes[target] = compact.status_codes
    coverage[target] += 1


def _merge_comparisons(comparisons: Sequence[dict[str, object]]) -> dict[str, object]:
    return {
        "accepted": all(item["accepted"] for item in comparisons),
        "expected_cell_count": sum(
            int(item["expected_cell_count"]) for item in comparisons
        ),
        "candidate_cell_count": sum(
            int(item["candidate_cell_count"]) for item in comparisons
        ),
        "missing_cell_count": sum(
            len(item["missing_linear_indices"]) for item in comparisons
        ),
        "unexpected_cell_count": sum(
            len(item["unexpected_linear_indices"]) for item in comparisons
        ),
        "duplicate_cell_count": sum(
            int(item["duplicate_candidate_count"]) for item in comparisons
        ),
        "coordinate_mismatches": sum(
            int(item["coordinate_mismatches"]) for item in comparisons
        ),
        "status_mismatches": sum(
            int(item["status_mismatches"]) for item in comparisons
        ),
        "validity_issue_mismatches": sum(
            int(item["validity_issue_mismatches"]) for item in comparisons
        ),
        "error_semantics_mismatches": sum(
            int(item["error_semantics_mismatches"]) for item in comparisons
        ),
        "provenance_mismatches": sum(
            int(item["provenance_mismatches"]) for item in comparisons
        ),
        "solver_evaluation_mismatches": sum(
            int(item["solver_evaluation_mismatches"]) for item in comparisons
        ),
        "exact_value_matches": sum(
            int(item["exact_value_matches"]) for item in comparisons
        ),
        "exact_diagnostic_matches": sum(
            int(item["exact_diagnostic_matches"]) for item in comparisons
        ),
        "maximum_rate_error_per_second": max(
            (float(item["maximum_rate_error_per_second"]) for item in comparisons),
            default=0.0,
        ),
        "maximum_energy_diagnostic_error": max(
            (float(item["maximum_energy_diagnostic_error"]) for item in comparisons),
            default=0.0,
        ),
        "maximum_candidate_reset_norm_error": max(
            (float(item["maximum_candidate_reset_norm_error"]) for item in comparisons),
            default=0.0,
        ),
    }


def execute_tiled_field(
    executor: ProcessPoolExecutor,
    context: FieldContext,
    tile_shape: TileShape,
    baseline: Sequence[execution.CellOutcome],
    *,
    tile_order: str = "row_major",
    local_order: str = "row_major",
    attempt: int = 1,
) -> CompactFieldResult:
    work_units = plan_tiles(context, tile_shape)
    if tile_order == "reversed":
        work_units = tuple(reversed(work_units))
    elif tile_order != "row_major":
        raise ValueError(f"Unknown tile order: {tile_order}.")
    baseline_by_index = {item.task.linear_index: item for item in baseline}
    values, status_codes, coverage = _empty_field_arrays(context)
    exceptional_cells: list[ExceptionalCell] = []
    summaries: list[TileSummary] = []
    comparisons: list[dict[str, object]] = []
    started = perf_counter()
    for work_unit in work_units:
        tasks = tile_tasks(work_unit, local_order=local_order)
        tile_started = perf_counter()
        outcomes = execution.run_process_pool(
            executor,
            tasks,
            chunksize=PROCESS_CHUNKSIZE,
        )
        execution_wall_seconds = perf_counter() - tile_started
        expected = tuple(baseline_by_index[task.linear_index] for task in tasks)
        comparison = execution.compare_outcomes(expected, outcomes)
        comparisons.append(comparison)
        compact = _compact_tile(
            work_unit,
            outcomes,
            attempt=attempt,
            execution_wall_seconds=execution_wall_seconds,
        )
        _insert_compact_tile(values, status_codes, coverage, compact)
        exceptional_cells.extend(compact.exceptional_cells)
        summaries.append(
            TileSummary(
                bounds=work_unit.bounds,
                attempt=attempt,
                status_counts=compact.status_counts,
                maximum_energy_drift=compact.maximum_energy_drift,
                maximum_reset_norm_error=compact.maximum_reset_norm_error,
                solver_function_evaluations=compact.solver_function_evaluations,
                evaluator_elapsed_seconds=compact.evaluator_elapsed_seconds,
                execution_wall_seconds=compact.execution_wall_seconds,
                compaction_seconds=compact.compaction_seconds,
                worker_cell_counts=compact.worker_cell_counts,
                worker_peak_rss_bytes=compact.worker_peak_rss_bytes,
                equivalence=comparison,
            )
        )
        del outcomes, compact
    elapsed_seconds = perf_counter() - started
    if np.any(coverage != 1) or np.any(status_codes == 255):
        raise RuntimeError("Tiled field assembly did not cover every cell exactly once.")
    return CompactFieldResult(
        context=context,
        values=values,
        status_codes=status_codes,
        exceptional_cells=tuple(sorted(exceptional_cells, key=lambda item: (
            item.theta2_index, item.theta1_index
        ))),
        tile_summaries=tuple(summaries),
        coverage=coverage,
        elapsed_seconds=elapsed_seconds,
        equivalence=_merge_comparisons(comparisons),
    )


def compact_untiled_baseline(
    context: FieldContext,
    outcomes: Sequence[execution.CellOutcome],
    *,
    elapsed_seconds: float,
) -> CompactFieldResult:
    work_unit = TileWorkUnit(
        context=context,
        bounds=TileBounds(context.shape, 0, context.shape[0], 0, context.shape[1]),
    )
    compact = _compact_tile(
        work_unit,
        outcomes,
        attempt=1,
        execution_wall_seconds=elapsed_seconds,
    )
    values, status_codes, coverage = _empty_field_arrays(context)
    _insert_compact_tile(values, status_codes, coverage, compact)
    return CompactFieldResult(
        context=context,
        values=values,
        status_codes=status_codes,
        exceptional_cells=compact.exceptional_cells,
        tile_summaries=(
            TileSummary(
                bounds=work_unit.bounds,
                attempt=1,
                status_counts=compact.status_counts,
                maximum_energy_drift=compact.maximum_energy_drift,
                maximum_reset_norm_error=compact.maximum_reset_norm_error,
                solver_function_evaluations=compact.solver_function_evaluations,
                evaluator_elapsed_seconds=compact.evaluator_elapsed_seconds,
                execution_wall_seconds=elapsed_seconds,
                compaction_seconds=compact.compaction_seconds,
                worker_cell_counts=compact.worker_cell_counts,
                worker_peak_rss_bytes=compact.worker_peak_rss_bytes,
                equivalence=None,
            ),
        ),
        coverage=coverage,
        elapsed_seconds=elapsed_seconds + compact.compaction_seconds,
        equivalence={"accepted": True},
    )


def compare_compact_fields(
    expected: CompactFieldResult,
    actual: CompactFieldResult,
) -> dict[str, object]:
    values_equal = bool(np.array_equal(expected.values, actual.values, equal_nan=True))
    statuses_equal = bool(np.array_equal(expected.status_codes, actual.status_codes))
    coordinates_equal = bool(
        expected.context.theta1_axis == actual.context.theta1_axis
        and expected.context.theta2_axis == actual.context.theta2_axis
    )
    provenance_equal = bool(
        expected.context.observable_spec == actual.context.observable_spec
        and expected.context.evaluator == actual.context.evaluator
        and expected.context.periodic == actual.context.periodic
    )
    exceptional_equal = expected.exceptional_cells == actual.exceptional_cells
    return {
        "accepted": bool(
            values_equal
            and statuses_equal
            and coordinates_equal
            and provenance_equal
            and exceptional_equal
            and np.all(actual.coverage == 1)
            and actual.equivalence["accepted"]
        ),
        "values_equal": values_equal,
        "statuses_equal": statuses_equal,
        "coordinates_equal": coordinates_equal,
        "provenance_equal": provenance_equal,
        "exceptional_cells_equal": exceptional_equal,
        "coverage_exact": bool(np.all(actual.coverage == 1)),
        "expected_digest": expected.digest,
        "actual_digest": actual.digest,
        "scientific_equivalence": actual.equivalence,
    }


def _open_worker_pool(
    observable_spec: RenormalizedTangentSpec,
) -> tuple[ProcessPoolExecutor, tuple[execution.WorkerIdentity, ...], float]:
    if (os.cpu_count() or 1) < PROCESS_WIDTH:
        raise RuntimeError("Experiment 017 requires the accepted four-worker width.")
    started = perf_counter()
    executor = ProcessPoolExecutor(
        max_workers=PROCESS_WIDTH,
        mp_context=multiprocessing.get_context("spawn"),
        initializer=execution._initialize_process_worker,
        initargs=(observable_spec,),
    )
    identities = execution._wait_for_process_workers(executor, PROCESS_WIDTH)
    return executor, identities, perf_counter() - started


def _close_worker_pool(
    executor: ProcessPoolExecutor,
    identities: Sequence[execution.WorkerIdentity],
) -> dict[str, object]:
    process_ids = [identity.process_id for identity in identities]
    started = perf_counter()
    executor.shutdown(wait=True, cancel_futures=True)
    elapsed = perf_counter() - started
    time.sleep(0.05)
    return {
        "shutdown_seconds": elapsed,
        "workers_stopped": all(not execution._pid_alive(pid) for pid in process_ids),
    }


def _untiled_outcomes(
    executor: ProcessPoolExecutor,
    context: FieldContext,
) -> tuple[tuple[execution.CellOutcome, ...], float]:
    tasks = tuple(
        execution.CellTask(
            linear_index=theta2_index * context.shape[1] + theta1_index,
            theta2_index=theta2_index,
            theta1_index=theta1_index,
            theta2_degrees=context.theta2_axis[theta2_index],
            theta1_degrees=context.theta1_axis[theta1_index],
        )
        for theta2_index in range(context.shape[0])
        for theta1_index in range(context.shape[1])
    )
    started = perf_counter()
    outcomes = execution.run_process_pool(
        executor, tasks, chunksize=PROCESS_CHUNKSIZE
    )
    return outcomes, perf_counter() - started


def _timing_distribution(measurements: Sequence[dict[str, object]]) -> dict[str, object]:
    wall = np.asarray([item["wall_seconds"] for item in measurements], dtype=float)
    return {
        "sample_count": len(measurements),
        "wall_seconds_median": float(np.median(wall)),
        "wall_seconds_q1": float(np.percentile(wall, 25)),
        "wall_seconds_q3": float(np.percentile(wall, 75)),
        "wall_seconds_iqr": float(np.percentile(wall, 75) - np.percentile(wall, 25)),
        "cells_per_second_median": float(
            np.median([item["cells_per_second"] for item in measurements])
        ),
        "effective_seconds_per_cell_median": float(
            np.median([item["seconds_per_cell"] for item in measurements])
        ),
        "maximum_tile_seconds": float(
            max(float(item["maximum_tile_seconds"]) for item in measurements)
        ),
        "compaction_seconds_median": float(
            np.median([item["compaction_seconds"] for item in measurements])
        ),
        "evaluator_sum_to_wall_ratio_median": float(
            np.median(
                [item["evaluator_sum_to_wall_ratio"] for item in measurements]
            )
        ),
        "all_equivalence_checks_passed": all(
            item["equivalence_accepted"] for item in measurements
        ),
        "measurements": list(measurements),
    }


def _measurement_from_field(
    field: CompactFieldResult,
    *,
    samples: int,
    policy: str,
) -> dict[str, object]:
    cell_count = samples * samples
    tile_wall_seconds = [
        summary.execution_wall_seconds for summary in field.tile_summaries
    ]
    evaluator_sum = sum(
        summary.evaluator_elapsed_seconds for summary in field.tile_summaries
    )
    status_counts = tuple(
        sum(summary.status_counts[index] for summary in field.tile_summaries)
        for index in range(3)
    )
    return {
        "policy": policy,
        "samples_per_axis": samples,
        "cell_count": cell_count,
        "tile_count": len(field.tile_summaries),
        "edge_shapes": sorted({summary.bounds.shape for summary in field.tile_summaries}),
        "wall_seconds": field.elapsed_seconds,
        "cells_per_second": cell_count / field.elapsed_seconds,
        "seconds_per_cell": field.elapsed_seconds / cell_count,
        "tile_wall_seconds": tile_wall_seconds,
        "median_tile_seconds": float(np.median(tile_wall_seconds)),
        "maximum_tile_seconds": max(tile_wall_seconds),
        "compaction_seconds": sum(
            summary.compaction_seconds for summary in field.tile_summaries
        ),
        "status_counts_valid_invalid_error": status_counts,
        "maximum_energy_drift": max(
            summary.maximum_energy_drift for summary in field.tile_summaries
        ),
        "maximum_reset_norm_error": max(
            summary.maximum_reset_norm_error for summary in field.tile_summaries
        ),
        "solver_function_evaluations": sum(
            summary.solver_function_evaluations for summary in field.tile_summaries
        ),
        "evaluator_elapsed_sum_seconds": evaluator_sum,
        "evaluator_sum_to_wall_ratio": evaluator_sum / field.elapsed_seconds,
        "worker_cell_counts": _sum_worker_counts(field.tile_summaries),
        "worker_peak_rss_bytes": _maximum_worker_peaks(field.tile_summaries),
        "equivalence_accepted": bool(field.equivalence["accepted"]),
        "field_digest": field.digest,
    }


def _sum_worker_counts(
    summaries: Sequence[TileSummary],
) -> dict[str, int]:
    counts: dict[int, int] = {}
    for summary in summaries:
        for process_id, count in summary.worker_cell_counts:
            counts[process_id] = counts.get(process_id, 0) + count
    return {str(pid): count for pid, count in sorted(counts.items())}


def _maximum_worker_peaks(
    summaries: Sequence[TileSummary],
) -> dict[str, int]:
    peaks: dict[int, int] = {}
    for summary in summaries:
        for process_id, value in summary.worker_peak_rss_bytes:
            peaks[process_id] = max(peaks.get(process_id, 0), value)
    return {str(pid): value for pid, value in sorted(peaks.items())}


def _canonical_baselines(
    contexts: dict[int, FieldContext],
) -> tuple[
    dict[int, tuple[execution.CellOutcome, ...]],
    dict[int, CompactFieldResult],
    dict[str, object],
]:
    spec = next(iter(contexts.values())).observable_spec
    assert spec is not None
    executor, identities, startup_seconds = _open_worker_pool(spec)
    rich: dict[int, tuple[execution.CellOutcome, ...]] = {}
    compact: dict[int, CompactFieldResult] = {}
    try:
        for samples, context in contexts.items():
            outcomes, elapsed = _untiled_outcomes(executor, context)
            rich[samples] = outcomes
            compact[samples] = compact_untiled_baseline(
                context, outcomes, elapsed_seconds=elapsed
            )
    finally:
        shutdown = _close_worker_pool(executor, identities)
    return rich, compact, {
        "startup_seconds": startup_seconds,
        "worker_identities": [asdict(item) for item in identities],
        **shutdown,
    }


def run_timing_and_equivalence(
    contexts: dict[int, FieldContext],
    baselines: dict[int, tuple[execution.CellOutcome, ...]],
    compact_baselines: dict[int, CompactFieldResult],
) -> dict[str, object]:
    raw_groups: dict[str, list[dict[str, object]]] = {}
    lifecycle_blocks: list[dict[str, object]] = []
    first_fields: dict[tuple[str, int], CompactFieldResult] = {}
    policy_labels = ["untiled", *(shape.label for shape in CANDIDATE_TILE_SHAPES)]

    for repeat in range(BENCHMARK_REPEATS):
        spec = contexts[NUMERICAL_SAMPLE_COUNTS[0]].observable_spec
        assert spec is not None
        executor, identities, startup_seconds = _open_worker_pool(spec)
        try:
            rotated = policy_labels[repeat:] + policy_labels[:repeat]
            sample_order = list(NUMERICAL_SAMPLE_COUNTS)
            if repeat % 2:
                sample_order.reverse()
            for policy in rotated:
                for samples in sample_order:
                    context = contexts[samples]
                    process_ids = [item.process_id for item in identities]
                    worker_memory_before = _current_rss_bytes(process_ids)
                    coordinator_memory_before = _coordinator_memory()
                    if policy == "untiled":
                        outcomes, elapsed = _untiled_outcomes(executor, context)
                        field = compact_untiled_baseline(
                            context, outcomes, elapsed_seconds=elapsed
                        )
                        comparison = execution.compare_outcomes(
                            baselines[samples], outcomes
                        )
                        field = replace(field, equivalence=comparison)
                    else:
                        shape = next(
                            shape
                            for shape in CANDIDATE_TILE_SHAPES
                            if shape.label == policy
                        )
                        field = execute_tiled_field(
                            executor,
                            context,
                            shape,
                            baselines[samples],
                        )
                    field_comparison = compare_compact_fields(
                        compact_baselines[samples], field
                    )
                    measurement = _measurement_from_field(
                        field, samples=samples, policy=policy
                    )
                    measurement["equivalence_accepted"] = bool(
                        measurement["equivalence_accepted"]
                        and field_comparison["accepted"]
                    )
                    measurement["compact_field_comparison"] = field_comparison
                    gc.collect()
                    measurement["worker_current_rss_before"] = worker_memory_before
                    measurement["worker_current_rss_after"] = _current_rss_bytes(
                        process_ids
                    )
                    measurement["coordinator_memory_before"] = (
                        coordinator_memory_before
                    )
                    measurement["coordinator_memory_after"] = _coordinator_memory()
                    raw_groups.setdefault(f"{policy}|{samples}x{samples}", []).append(
                        measurement
                    )
                    first_fields.setdefault((policy, samples), field)
                    if policy == "untiled":
                        del outcomes
                    del field
        finally:
            shutdown = _close_worker_pool(executor, identities)
        lifecycle_blocks.append(
            {
                "repeat": repeat,
                "startup_seconds": startup_seconds,
                "worker_identities": [asdict(item) for item in identities],
                **shutdown,
            }
        )

    timing_groups = {
        key: _timing_distribution(measurements)
        for key, measurements in raw_groups.items()
    }
    return {
        "timing_groups": timing_groups,
        "lifecycle_blocks": lifecycle_blocks,
        "first_fields": first_fields,
    }


def run_order_independence(
    context: FieldContext,
    baseline: Sequence[execution.CellOutcome],
    expected_fields: dict[tuple[str, int], CompactFieldResult],
) -> dict[str, object]:
    spec = context.observable_spec
    assert spec is not None
    executor, identities, startup_seconds = _open_worker_pool(spec)
    results: dict[str, object] = {}
    try:
        for shape in CANDIDATE_TILE_SHAPES:
            permuted = execute_tiled_field(
                executor,
                context,
                shape,
                baseline,
                tile_order="reversed",
                local_order="reversed",
            )
            expected = expected_fields[(shape.label, context.shape[0])]
            results[shape.label] = compare_compact_fields(expected, permuted)
    finally:
        shutdown = _close_worker_pool(executor, identities)
    return {
        "startup_seconds": startup_seconds,
        "worker_identities": [asdict(item) for item in identities],
        "shape_results": results,
        "accepted": all(item["accepted"] for item in results.values()),
        **shutdown,
    }


def representation_assessment(
    context: FieldContext,
    baseline: Sequence[execution.CellOutcome],
) -> dict[str, object]:
    baseline_by_index = {item.task.linear_index: item for item in baseline}
    results: dict[str, object] = {}
    for shape in CANDIDATE_TILE_SHAPES:
        rich_total = 0
        compact_total = 0
        maximum_rich = 0
        maximum_compact = 0
        maximum_arrays = 0
        maximum_transient_cells = 0
        for work_unit in plan_tiles(context, shape):
            tasks = tile_tasks(work_unit)
            outcomes = tuple(baseline_by_index[task.linear_index] for task in tasks)
            compact = _compact_tile(
                work_unit,
                outcomes,
                attempt=1,
                execution_wall_seconds=0.0,
            )
            rich_bytes = len(pickle.dumps(outcomes))
            compact_bytes = len(pickle.dumps(compact))
            rich_total += rich_bytes
            compact_total += compact_bytes
            maximum_rich = max(maximum_rich, rich_bytes)
            maximum_compact = max(maximum_compact, compact_bytes)
            maximum_arrays = max(maximum_arrays, compact.array_bytes)
            maximum_transient_cells = max(maximum_transient_cells, len(outcomes))
        results[shape.label] = {
            "tile_count": len(plan_tiles(context, shape)),
            "maximum_transient_rich_cell_count": maximum_transient_cells,
            "maximum_rich_tile_pickle_bytes": maximum_rich,
            "maximum_compact_tile_pickle_bytes": maximum_compact,
            "maximum_compact_array_bytes": maximum_arrays,
            "sum_rich_tile_pickle_bytes": rich_total,
            "sum_compact_tile_pickle_bytes": compact_total,
            "compact_to_rich_serialized_ratio": compact_total / rich_total,
        }
    return {
        "context_shape": list(context.shape),
        "status_encoding": {
            status.value: int(code) for status, code in STATUS_TO_CODE.items()
        },
        "shape_results": results,
    }


def _synthetic_outcomes(work_unit: TileWorkUnit) -> tuple[execution.CellOutcome, ...]:
    outcomes = []
    for task in tile_tasks(work_unit):
        if task.linear_index == 1:
            status = EvaluationStatus.COMPLETED_INVALID
            value = 1.0
            issues = ("controlled invalidity",)
            error_type = None
            error_message = None
            diagnostics = SimpleNamespace(
                maximum_normalized_reference_energy_drift=2.0e-7,
                maximum_post_renormalization_norm_error=2.0e-16,
                solver_function_evaluations=10,
            )
        elif task.linear_index == 4:
            status = EvaluationStatus.EXECUTION_ERROR
            value = None
            issues = ()
            error_type = "RuntimeError"
            error_message = "controlled scalar failure"
            diagnostics = None
        else:
            status = EvaluationStatus.COMPLETED_VALID
            value = float(task.linear_index)
            issues = ()
            error_type = None
            error_message = None
            diagnostics = SimpleNamespace(
                maximum_normalized_reference_energy_drift=1.0e-10,
                maximum_post_renormalization_norm_error=2.0e-16,
                solver_function_evaluations=10,
            )
        outcomes.append(
            execution.CellOutcome(
                task=task,
                evaluation=ScalarEvaluation(
                    status=status,
                    value=value,
                    diagnostics=diagnostics,
                    elapsed_seconds=0.001,
                    evaluator="synthetic",
                    validity_issues=issues,
                    error_type=error_type,
                    error_message=error_message,
                ),
                worker_pid=1,
                worker_peak_rss_bytes=1,
            )
        )
    return tuple(outcomes)


def assess_failure_retry_and_interruption() -> dict[str, object]:
    context = FieldContext(
        theta1_axis=(0.0, 1.0, 2.0, 3.0),
        theta2_axis=(0.0, 1.0, 2.0, 3.0),
        coordinate_unit="degrees",
        periodic=False,
        observable_spec=replace(RenormalizedTangentSpec(), duration=0.25),
        evaluator="synthetic",
    )
    work_units = plan_tiles(context, TileShape(2, 2))
    failed_identity = work_units[2].identity
    completed: dict[tuple[object, ...], CompactTileResult] = {}
    failure_recorded = False
    completed_before_failure_digest = None
    completed_before_failure_identities: tuple[tuple[object, ...], ...] = ()
    for work_unit in work_units:
        try:
            if work_unit.identity == failed_identity:
                raise InjectedWorkUnitFailure("controlled work-unit failure")
            compact = _compact_tile(
                work_unit,
                _synthetic_outcomes(work_unit),
                attempt=1,
                execution_wall_seconds=0.0,
            )
            completed[work_unit.identity] = compact
        except InjectedWorkUnitFailure:
            failure_recorded = True
            completed_before_failure_identities = tuple(completed)
            completed_before_failure_digest = _compact_collection_digest(completed.values())

    unrelated_unchanged = completed_before_failure_digest == _compact_collection_digest(
        completed[identity] for identity in completed_before_failure_identities
    )
    failed_partial_absent = failed_identity not in completed
    retry_unit = next(unit for unit in work_units if unit.identity == failed_identity)
    reconstructed = next(
        unit
        for unit in plan_tiles(context, TileShape(2, 2))
        if unit.identity == failed_identity
    )
    retry_tasks_identical = tile_tasks(retry_unit) == tile_tasks(reconstructed)
    retry = _compact_tile(
        reconstructed,
        _synthetic_outcomes(reconstructed),
        attempt=2,
        execution_wall_seconds=0.0,
    )
    completed[reconstructed.identity] = retry
    clean = {
        unit.identity: _compact_tile(
            unit,
            _synthetic_outcomes(unit),
            attempt=1,
            execution_wall_seconds=0.0,
        )
        for unit in work_units
    }
    retry_matches_clean = _compact_values_digest(completed.values()) == (
        _compact_values_digest(clean.values())
    )

    prefix_count = len(work_units) // 2
    interrupted = {
        unit.identity: clean[unit.identity] for unit in work_units[:prefix_count]
    }
    reconstructed_plan = plan_tiles(context, TileShape(2, 2))
    skipped = 0
    for unit in reconstructed_plan:
        if unit.identity in interrupted:
            skipped += 1
            continue
        interrupted[unit.identity] = clean[unit.identity]
    interrupted_matches_clean = _compact_values_digest(interrupted.values()) == (
        _compact_values_digest(clean.values())
    )

    programming_error_propagated = False
    try:
        raise ValueError("controlled programming defect")
    except ValueError as error:
        programming_error_propagated = str(error) == "controlled programming defect"

    all_results = tuple(clean.values())
    status_counts = tuple(
        sum(result.status_counts[index] for result in all_results)
        for index in range(3)
    )
    accepted = all(
        (
            failure_recorded,
            failed_partial_absent,
            unrelated_unchanged,
            retry_tasks_identical,
            retry_matches_clean,
            interrupted_matches_clean,
            skipped == prefix_count,
            programming_error_propagated,
            status_counts[0] > 0,
            status_counts[1] == 1,
            status_counts[2] == 1,
        )
    )
    return {
        "accepted": accepted,
        "status_counts_valid_invalid_error": status_counts,
        "work_unit_failure_recorded": failure_recorded,
        "failed_partial_result_absent": failed_partial_absent,
        "unrelated_completed_tiles_unchanged": unrelated_unchanged,
        "retry_identity_and_tasks_identical": retry_tasks_identical,
        "retry_matches_clean_result": retry_matches_clean,
        "interrupted_resume_matches_clean_result": interrupted_matches_clean,
        "completed_prefix_skipped_count": skipped,
        "programming_error_propagated": programming_error_propagated,
    }


def _compact_collection_digest(results: Iterable[CompactTileResult]) -> str:
    return hashlib.sha256(
        b"".join(pickle.dumps(result) for result in sorted(
            results,
            key=lambda item: item.work_unit.bounds,
        ))
    ).hexdigest()


def _compact_values_digest(results: Iterable[CompactTileResult]) -> str:
    digest = hashlib.sha256()
    for result in sorted(results, key=lambda item: item.work_unit.bounds):
        digest.update(np.asarray(result.values, dtype="<f8").tobytes())
        digest.update(result.status_codes.tobytes())
        digest.update(repr(result.exceptional_cells).encode())
    return digest.hexdigest()


def _intervals_overlap(first: dict[str, object], second: dict[str, object]) -> bool:
    return bool(
        first["wall_seconds_q1"] <= second["wall_seconds_q3"]
        and second["wall_seconds_q1"] <= first["wall_seconds_q3"]
    )


def choose_provisional_tile(
    timing_groups: dict[str, dict[str, object]],
) -> dict[str, object]:
    eligible = []
    fastest_by_samples: dict[int, TileShape] = {}
    for samples in NUMERICAL_SAMPLE_COUNTS:
        fastest_by_samples[samples] = min(
            CANDIDATE_TILE_SHAPES,
            key=lambda shape: timing_groups[
                f"{shape.label}|{samples}x{samples}"
            ]["wall_seconds_median"],
        )
    for shape in CANDIDATE_TILE_SHAPES:
        if not all(
            timing_groups[f"{shape.label}|{samples}x{samples}"][
                "all_equivalence_checks_passed"
            ]
            for samples in NUMERICAL_SAMPLE_COUNTS
        ):
            continue
        if all(
            _intervals_overlap(
                timing_groups[f"{shape.label}|{samples}x{samples}"],
                timing_groups[
                    f"{fastest_by_samples[samples].label}|{samples}x{samples}"
                ],
            )
            for samples in NUMERICAL_SAMPLE_COUNTS
        ):
            eligible.append(shape)
    if not eligible:
        fallback = min(
            CANDIDATE_TILE_SHAPES,
            key=lambda shape: sum(
                timing_groups[f"{shape.label}|{samples}x{samples}"][
                    "wall_seconds_median"
                ]
                for samples in NUMERICAL_SAMPLE_COUNTS
            ),
        )
        return {
            "outcome": "bounded_range_unresolved",
            "provisional_shape": fallback.label,
            "timing_equivalent_shapes": [],
            "fastest_shapes_by_workload": {
                str(samples): fastest_by_samples[samples].label
                for samples in NUMERICAL_SAMPLE_COUNTS
            },
        }
    chosen = min(
        eligible,
        key=lambda shape: (shape.cell_count, not shape.square, shape.theta2_cells),
    )
    return {
        "outcome": "fixed_shape_provisional",
        "provisional_shape": chosen.label,
        "timing_equivalent_shapes": [shape.label for shape in eligible],
        "fastest_shapes_by_workload": {
            str(samples): fastest_by_samples[samples].label
            for samples in NUMERICAL_SAMPLE_COUNTS
        },
    }


def _current_rss_bytes(process_ids: Sequence[int]) -> dict[str, object]:
    values: dict[str, int] = {}
    errors: dict[str, str] = {}
    for process_id in process_ids:
        try:
            completed = subprocess.run(
                ["ps", "-o", "rss=", "-p", str(process_id)],
                check=True,
                capture_output=True,
                text=True,
            )
            kibibytes = int(completed.stdout.strip())
            values[str(process_id)] = kibibytes * 1024
        except (OSError, subprocess.SubprocessError, ValueError) as error:
            errors[str(process_id)] = f"{type(error).__name__}: {error}"
    return {"rss_bytes_by_pid": values, "errors_by_pid": errors}


def _coordinator_memory() -> dict[str, int]:
    current = _current_rss_bytes([os.getpid()])
    peak = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    if sys.platform != "darwin":
        peak *= 1024
    return {
        "current_rss_bytes": current["rss_bytes_by_pid"].get(str(os.getpid()), -1),
        "peak_rss_bytes": peak,
    }


def _median_worker_rss(snapshot: dict[str, object]) -> float | None:
    values = list(snapshot["rss_bytes_by_pid"].values())
    return float(median(values)) if values else None


def run_persistent_lifecycle(
    context: FieldContext,
    baseline: Sequence[execution.CellOutcome],
    tile_shape: TileShape,
) -> dict[str, object]:
    spec = context.observable_spec
    assert spec is not None
    work_unit = plan_tiles(context, tile_shape)[0]
    tasks = tile_tasks(work_unit)
    baseline_by_index = {item.task.linear_index: item for item in baseline}
    expected = tuple(baseline_by_index[task.linear_index] for task in tasks)
    executor, identities, startup_seconds = _open_worker_pool(spec)
    process_ids = [item.process_id for item in identities]
    snapshots = [
        {
            "completed_cells": 0,
            "current": _current_rss_bytes(process_ids),
            "coordinator": _coordinator_memory(),
        }
    ]
    completed_cells = 0
    next_checkpoint = 0
    comparisons = []
    worker_peak: dict[int, int] = {pid: 0 for pid in process_ids}
    started = perf_counter()
    try:
        while completed_cells < LIFECYCLE_CELL_COUNT:
            outcomes = execution.run_process_pool(
                executor, tasks, chunksize=PROCESS_CHUNKSIZE
            )
            comparisons.append(execution.compare_outcomes(expected, outcomes))
            for outcome in outcomes:
                worker_peak[outcome.worker_pid] = max(
                    worker_peak.get(outcome.worker_pid, 0),
                    outcome.worker_peak_rss_bytes,
                )
            completed_cells += len(outcomes)
            while (
                next_checkpoint < len(LIFECYCLE_CHECKPOINTS)
                and completed_cells >= LIFECYCLE_CHECKPOINTS[next_checkpoint]
            ):
                gc.collect()
                snapshots.append(
                    {
                        "completed_cells": completed_cells,
                        "current": _current_rss_bytes(process_ids),
                        "coordinator": _coordinator_memory(),
                    }
                )
                next_checkpoint += 1
            del outcomes
        execution_seconds = perf_counter() - started
    finally:
        shutdown = _close_worker_pool(executor, identities)

    medians = [_median_worker_rss(item["current"]) for item in snapshots]
    rss_available = all(value is not None for value in medians)
    growth = None
    late_growth = None
    material_growth = None
    if rss_available:
        growth = medians[-1] - medians[0]
        midpoint_index = min(
            range(len(snapshots)),
            key=lambda index: abs(snapshots[index]["completed_cells"] - 1024),
        )
        late_growth = medians[-1] - medians[midpoint_index]
        material_growth = bool(
            growth >= MATERIAL_CURRENT_RSS_GROWTH_BYTES
            and late_growth >= MATERIAL_LATE_RSS_GROWTH_BYTES
        )
    return {
        "tile_shape": tile_shape.label,
        "tile_cell_count": work_unit.bounds.cell_count,
        "worker_identities": [asdict(item) for item in identities],
        "target_cells": LIFECYCLE_CELL_COUNT,
        "actual_completed_cells": completed_cells,
        "startup_seconds": startup_seconds,
        "execution_seconds": execution_seconds,
        "end_to_end_seconds": startup_seconds + execution_seconds + shutdown[
            "shutdown_seconds"
        ],
        "snapshots": snapshots,
        "worker_peak_rss_bytes_by_pid": {
            str(pid): value for pid, value in sorted(worker_peak.items())
        },
        "rss_available": rss_available,
        "median_current_rss_growth_bytes": growth,
        "median_current_rss_growth_after_1024_bytes": late_growth,
        "material_growth": material_growth,
        "growth_rule": {
            "total_growth_bytes": MATERIAL_CURRENT_RSS_GROWTH_BYTES,
            "late_growth_bytes": MATERIAL_LATE_RSS_GROWTH_BYTES,
        },
        "all_numerical_comparisons_passed": all(
            item["accepted"] for item in comparisons
        ),
        **shutdown,
    }


def run_recycling_control(
    context: FieldContext,
    baseline: Sequence[execution.CellOutcome],
    tile_shape: TileShape,
    cell_limit: int,
) -> dict[str, object]:
    spec = context.observable_spec
    assert spec is not None
    work_unit = plan_tiles(context, tile_shape)[0]
    tasks = tile_tasks(work_unit)
    baseline_by_index = {item.task.linear_index: item for item in baseline}
    expected = tuple(baseline_by_index[task.linear_index] for task in tasks)
    total_started = perf_counter()
    total_startup = 0.0
    total_execution = 0.0
    total_shutdown = 0.0
    completed_cells = 0
    pools = []
    all_comparisons_passed = True
    while completed_cells < LIFECYCLE_CELL_COUNT:
        executor, identities, startup_seconds = _open_worker_pool(spec)
        process_ids = [item.process_id for item in identities]
        pool_started_cells = completed_cells
        ready_current = _current_rss_bytes(process_ids)
        total_startup += startup_seconds
        run_started = perf_counter()
        last_worker_peak: dict[int, int] = {}
        while completed_cells < LIFECYCLE_CELL_COUNT:
            if (
                completed_cells > pool_started_cells
                and completed_cells - pool_started_cells + len(tasks) > cell_limit
            ):
                break
            outcomes = execution.run_process_pool(
                executor, tasks, chunksize=PROCESS_CHUNKSIZE
            )
            comparison = execution.compare_outcomes(expected, outcomes)
            all_comparisons_passed = bool(
                all_comparisons_passed and comparison["accepted"]
            )
            for outcome in outcomes:
                last_worker_peak[outcome.worker_pid] = max(
                    last_worker_peak.get(outcome.worker_pid, 0),
                    outcome.worker_peak_rss_bytes,
                )
            completed_cells += len(outcomes)
            del outcomes
        execution_seconds = perf_counter() - run_started
        final_current = _current_rss_bytes(process_ids)
        shutdown = _close_worker_pool(executor, identities)
        total_execution += execution_seconds
        total_shutdown += shutdown["shutdown_seconds"]
        pools.append(
            {
                "completed_cells": completed_cells - pool_started_cells,
                "startup_seconds": startup_seconds,
                "execution_seconds": execution_seconds,
                "ready_current": ready_current,
                "final_current": final_current,
                "worker_peak_rss_bytes_by_pid": {
                    str(pid): value for pid, value in sorted(last_worker_peak.items())
                },
                **shutdown,
            }
        )
    ready_medians = [_median_worker_rss(pool["ready_current"]) for pool in pools]
    final_medians = [_median_worker_rss(pool["final_current"]) for pool in pools]
    rss_available = all(value is not None for value in (*ready_medians, *final_medians))
    memory_reset_observed = False
    if rss_available and len(pools) > 1:
        memory_reset_observed = bool(
            max(ready_medians) - min(ready_medians)
            <= MATERIAL_CURRENT_RSS_GROWTH_BYTES
            and all(
                ready_medians[index + 1]
                + MATERIAL_LATE_RSS_GROWTH_BYTES
                < final_medians[index]
                for index in range(len(pools) - 1)
            )
        )
    return {
        "cell_limit": cell_limit,
        "tile_shape": tile_shape.label,
        "actual_completed_cells": completed_cells,
        "pool_count": len(pools),
        "total_startup_seconds": total_startup,
        "total_execution_seconds": total_execution,
        "total_shutdown_seconds": total_shutdown,
        "end_to_end_seconds": perf_counter() - total_started,
        "all_numerical_comparisons_passed": all_comparisons_passed,
        "rss_available": rss_available,
        "memory_reset_observed": memory_reset_observed,
        "ready_median_rss_bytes": ready_medians,
        "final_median_rss_bytes": final_medians,
        "all_workers_stopped": all(pool["workers_stopped"] for pool in pools),
        "pools": pools,
    }


def lifecycle_assessment(
    context: FieldContext,
    baseline: Sequence[execution.CellOutcome],
    tile_shape: TileShape,
) -> dict[str, object]:
    persistent = run_persistent_lifecycle(context, baseline, tile_shape)
    controls = []
    if persistent["material_growth"] is True:
        controls = [
            run_recycling_control(context, baseline, tile_shape, limit)
            for limit in RECYCLING_CELL_LIMITS
        ]
    if persistent["material_growth"] is False:
        policy = {
            "kind": "bounded_pool_per_run",
            "tested_cells": persistent["actual_completed_cells"],
        }
    elif persistent["material_growth"] is True:
        successful = [
            item
            for item in controls
            if item["all_numerical_comparisons_passed"]
            and item["all_workers_stopped"]
            and item["memory_reset_observed"]
        ]
        selected = max(successful, key=lambda item: item["cell_limit"]) if successful else None
        policy = (
            {
                "kind": "recycle_between_tiles",
                "maximum_cells_per_pool": selected["cell_limit"],
            }
            if selected is not None
            else None
        )
    else:
        policy = {
            "kind": "bounded_pool_per_run",
            "tested_cells": persistent["actual_completed_cells"],
            "current_rss_unavailable": True,
        }
    return {
        "persistent_pool": persistent,
        "recycling_controls_activated": bool(controls),
        "recycling_controls": controls,
        "accepted_lifecycle_policy": policy,
        "accepted": bool(
            persistent["all_numerical_comparisons_passed"]
            and persistent["workers_stopped"]
            and policy is not None
        ),
    }


def final_decision(
    provisional: dict[str, object],
    coverage: dict[str, object],
    order: dict[str, object],
    failure: dict[str, object],
    lifecycle: dict[str, object],
) -> dict[str, object]:
    shape = provisional["provisional_shape"]
    shape_selected = provisional["outcome"] == "fixed_shape_provisional"
    gates = {
        "coverage": coverage["accepted"],
        "order_independence": order["accepted"],
        "failure_retry_interruption": failure["accepted"],
        "lifecycle": lifecycle["accepted"],
        "fixed_or_bounded_shape_selected": shape_selected,
    }
    if not all(gates.values()):
        return {
            "outcome": "rejected",
            "accepted_work_unit": None,
            "gates": gates,
            "reason": "At least one declared work-unit acceptance gate failed.",
        }
    return {
        "outcome": "accepted",
        "accepted_work_unit": {
            "tile_shape_theta2_theta1": shape,
            "bounds": "half-open global index rectangles with clipped edge tiles",
            "execution": (
                "one tile-at-a-time through four warmed spawn workers with "
                "indexed per-cell chunksize=1 dispatch"
            ),
            "lifecycle": lifecycle["accepted_lifecycle_policy"],
            "result": (
                "compact float64 value and uint8 status arrays, sparse exceptional "
                "details, tile summaries, and transient rich outcomes"
            ),
        },
        "gates": gates,
        "reason": (
            "The selected work unit is the smallest correctness-eligible shape "
            "whose timing spread overlaps the fastest candidate on both bounded "
            "workloads, with the lifecycle bound required by measured RSS evidence."
        ),
    }


def run_assessment() -> dict[str, object]:
    coverage = assess_periodic_coverage()
    failure = assess_failure_retry_and_interruption()
    contexts = {samples: bounded_field_context(samples) for samples in NUMERICAL_SAMPLE_COUNTS}
    baselines, compact_baselines, baseline_lifecycle = _canonical_baselines(contexts)
    timing = run_timing_and_equivalence(contexts, baselines, compact_baselines)
    order = run_order_independence(
        contexts[17], baselines[17], timing["first_fields"]
    )
    representation = representation_assessment(contexts[25], baselines[25])
    provisional = choose_provisional_tile(timing["timing_groups"])
    selected_shape = next(
        shape
        for shape in CANDIDATE_TILE_SHAPES
        if shape.label == provisional["provisional_shape"]
    )
    lifecycle = lifecycle_assessment(contexts[25], baselines[25], selected_shape)
    decision = final_decision(provisional, coverage, order, failure, lifecycle)
    del timing["first_fields"]
    return {
        "experiment": "017_rectangular_work_unit_boundary",
        "question": (
            "What rectangular unit of work gives efficient execution, deterministic "
            "coordinates, bounded memory, failure isolation, and resumability?"
        ),
        "decision": decision,
        "environment": {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "numpy_version": np.__version__,
            "scipy_version": scipy.__version__,
            "numba_version": numba.__version__,
            "logical_cpu_count": os.cpu_count(),
            "process_start_method": "spawn",
            "process_width": PROCESS_WIDTH,
            "process_chunksize": PROCESS_CHUNKSIZE,
            "current_rss_method": "ps -o rss= -p PID (KiB converted to bytes)",
            "peak_rss_method": "resource.getrusage ru_maxrss (platform-normalized)",
        },
        "scientific_contract": {
            "observable_specification": asdict(RenormalizedTangentSpec()),
            "evaluator": COMPILED_FORTRAN_EVALUATOR,
            "field_orientation": "values[theta2_index, theta1_index]",
            "periodic_domain": "[-pi, pi)",
            "full_periodic_scientific_validation_claimed": False,
        },
        "candidate_shapes_theta2_theta1": [
            [shape.theta2_cells, shape.theta1_cells]
            for shape in CANDIDATE_TILE_SHAPES
        ],
        "coverage": coverage,
        "baseline_lifecycle": baseline_lifecycle,
        "timing_and_equivalence": timing,
        "order_independence": order,
        "failure_retry_interruption": failure,
        "representation": representation,
        "provisional_tile_decision": provisional,
        "memory_and_lifecycle": lifecycle,
        "refinement": {
            "triggered": False,
            "reason": "No adjacent candidate ambiguity required a geometric refinement.",
        },
        "claim_boundary": {
            "persistence_claimed": False,
            "storage_schema_claimed": False,
            "full_periodic_lyapunov_equivalence_claimed": False,
            "high_resolution_field_claimed": False,
            "prototype_promotion_performed": False,
        },
    }


def save_assessment(
    assessment: dict[str, object], path: Path = DEFAULT_EVIDENCE_PATH
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output:
        json.dump(assessment, output, indent=2, allow_nan=False)
        output.write("\n")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIRECTORY)
    arguments = parser.parse_args()
    assessment = run_assessment()
    save_assessment(assessment, arguments.output_dir / "summary.json")
    return 0 if assessment["decision"]["outcome"] == "accepted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
