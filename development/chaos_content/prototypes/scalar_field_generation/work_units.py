"""Deterministic rectangular work units for two-axis scalar fields."""

from __future__ import annotations

from dataclasses import dataclass
from numbers import Integral
from typing import Sequence

import numpy as np


@dataclass(frozen=True, order=True)
class TileShape:
    """Nominal tile size in stored ``(theta2, theta1)`` order."""

    theta2_cells: int
    theta1_cells: int

    def __post_init__(self) -> None:
        for name, value in (
            ("theta2_cells", self.theta2_cells),
            ("theta1_cells", self.theta1_cells),
        ):
            if isinstance(value, bool) or not isinstance(value, Integral) or value <= 0:
                raise ValueError(f"{name} must be a positive integer.")

    @property
    def cell_count(self) -> int:
        return int(self.theta2_cells * self.theta1_cells)


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
            raise ValueError("theta2 bounds must be nonempty, half-open, and in range.")
        if not (0 <= self.theta1_start < self.theta1_stop <= theta1_samples):
            raise ValueError("theta1 bounds must be nonempty, half-open, and in range.")

    @property
    def shape(self) -> tuple[int, int]:
        return (
            self.theta2_stop - self.theta2_start,
            self.theta1_stop - self.theta1_start,
        )

    @property
    def cell_count(self) -> int:
        return self.shape[0] * self.shape[1]

    @property
    def as_tuple(self) -> tuple[int, int, int, int]:
        return (
            self.theta2_start,
            self.theta2_stop,
            self.theta1_start,
            self.theta1_stop,
        )

    def global_indices(self, local_theta2: int, local_theta1: int) -> tuple[int, int]:
        if not 0 <= local_theta2 < self.shape[0]:
            raise IndexError("local theta2 index is outside the work unit.")
        if not 0 <= local_theta1 < self.shape[1]:
            raise IndexError("local theta1 index is outside the work unit.")
        return (
            self.theta2_start + local_theta2,
            self.theta1_start + local_theta1,
        )


@dataclass(frozen=True, order=True)
class TileWorkUnit:
    index: int
    bounds: TileBounds

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError("Work-unit index must be nonnegative.")


@dataclass(frozen=True)
class ScalarCellTask:
    """Coordinate-neutral cell identity passed to an observable adapter."""

    linear_index: int
    theta2_index: int
    theta1_index: int
    theta2_coordinate: float
    theta1_coordinate: float


@dataclass(frozen=True)
class CoverageValidation:
    accepted: bool
    expected_cell_count: int
    planned_cell_count: int
    missing_cell_count: int
    overlapped_cell_count: int
    maximum_coverage_count: int


def plan_tiles(
    field_shape: tuple[int, int],
    tile_shape: TileShape,
) -> tuple[TileWorkUnit, ...]:
    """Plan row-major, clipped work units for a ``[theta2, theta1]`` field."""

    theta2_samples, theta1_samples = field_shape
    if theta2_samples <= 0 or theta1_samples <= 0:
        raise ValueError("Field dimensions must be positive.")
    bounds = (
        TileBounds(
            global_shape=field_shape,
            theta2_start=theta2_start,
            theta2_stop=min(theta2_start + tile_shape.theta2_cells, theta2_samples),
            theta1_start=theta1_start,
            theta1_stop=min(theta1_start + tile_shape.theta1_cells, theta1_samples),
        )
        for theta2_start in range(0, theta2_samples, tile_shape.theta2_cells)
        for theta1_start in range(0, theta1_samples, tile_shape.theta1_cells)
    )
    return tuple(
        TileWorkUnit(index=index, bounds=tile_bounds)
        for index, tile_bounds in enumerate(bounds)
    )


def tasks_for_work_unit(
    work_unit: TileWorkUnit,
    theta1_axis: Sequence[float],
    theta2_axis: Sequence[float],
) -> tuple[ScalarCellTask, ...]:
    """Return row-major tasks with exact global indices and stored coordinates."""

    bounds = work_unit.bounds
    if len(theta2_axis) != bounds.global_shape[0] or len(theta1_axis) != bounds.global_shape[1]:
        raise ValueError("Axis lengths must match the work unit's global field shape.")
    theta1_samples = bounds.global_shape[1]
    return tuple(
        ScalarCellTask(
            linear_index=theta2_index * theta1_samples + theta1_index,
            theta2_index=theta2_index,
            theta1_index=theta1_index,
            theta2_coordinate=float(theta2_axis[theta2_index]),
            theta1_coordinate=float(theta1_axis[theta1_index]),
        )
        for theta2_index in range(bounds.theta2_start, bounds.theta2_stop)
        for theta1_index in range(bounds.theta1_start, bounds.theta1_stop)
    )


def validate_tile_plan(
    field_shape: tuple[int, int],
    work_units: Sequence[TileWorkUnit],
) -> CoverageValidation:
    """Prove that a plan covers each global cell exactly once."""

    if not work_units:
        raise ValueError("A tile plan must contain at least one work unit.")
    coverage = np.zeros(field_shape, dtype=np.uint32)
    seen_indices: set[int] = set()
    planned_cells = 0
    for work_unit in work_units:
        if work_unit.index in seen_indices:
            raise ValueError("Work-unit indices must be unique.")
        seen_indices.add(work_unit.index)
        bounds = work_unit.bounds
        if bounds.global_shape != field_shape:
            raise ValueError("A work unit uses a different global field shape.")
        coverage[
            bounds.theta2_start : bounds.theta2_stop,
            bounds.theta1_start : bounds.theta1_stop,
        ] += 1
        planned_cells += bounds.cell_count
    missing = int(np.count_nonzero(coverage == 0))
    overlapped = int(np.count_nonzero(coverage > 1))
    return CoverageValidation(
        accepted=missing == 0 and overlapped == 0,
        expected_cell_count=int(np.prod(field_shape)),
        planned_cell_count=planned_cells,
        missing_cell_count=missing,
        overlapped_cell_count=overlapped,
        maximum_coverage_count=int(np.max(coverage)),
    )
