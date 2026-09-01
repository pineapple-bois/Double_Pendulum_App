"""Small rectangular initial-angle grids of the trusted finite-time observable."""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from time import perf_counter

import numpy as np

if __package__:
    from .reference import RenormalizedTangentSpec
    from .sweep import (
        SweepSampleStatus,
        Theta1SweepSample,
        Theta1SweepSpec,
        run_theta1_sweep,
    )
else:
    from reference import RenormalizedTangentSpec
    from sweep import (
        SweepSampleStatus,
        Theta1SweepSample,
        Theta1SweepSpec,
        run_theta1_sweep,
    )


@dataclass(frozen=True)
class Theta1Theta2GridSpec:
    """One ordered rectangle in initial ``theta1``--``theta2`` coordinates."""

    theta1_degrees: tuple[float, ...]
    theta2_degrees: tuple[float, ...]
    observable_spec: RenormalizedTangentSpec = field(
        default_factory=RenormalizedTangentSpec
    )

    def __post_init__(self) -> None:
        _validate_axis(self.theta1_degrees, "theta1_degrees")
        _validate_axis(self.theta2_degrees, "theta2_degrees")

    @property
    def shape(self) -> tuple[int, int]:
        """Return ``(theta2_count, theta1_count)`` in stored-array order."""

        return (len(self.theta2_degrees), len(self.theta1_degrees))


@dataclass(frozen=True)
class Theta1Theta2GridCell:
    """One grid cell wrapping the established 1-D sample outcome."""

    theta2_index: int
    theta1_index: int
    theta2_degrees: float
    theta1_sample: Theta1SweepSample

    @property
    def theta1_degrees(self) -> float:
        return self.theta1_sample.theta1_degrees

    @property
    def status(self) -> SweepSampleStatus:
        return self.theta1_sample.status

    @property
    def finite_time_stretching_rate(self) -> float | None:
        return self.theta1_sample.finite_time_stretching_rate

    @property
    def numerically_valid(self) -> bool:
        return self.theta1_sample.numerically_valid


@dataclass(frozen=True)
class Theta1Theta2GridResult:
    """A rectangular field stored as ``[theta2_index, theta1_index]``."""

    spec: Theta1Theta2GridSpec
    cells: tuple[tuple[Theta1Theta2GridCell, ...], ...]
    elapsed_seconds: float

    @property
    def shape(self) -> tuple[int, int]:
        return self.spec.shape

    @property
    def cell_count(self) -> int:
        return self.shape[0] * self.shape[1]

    @property
    def theta1_axis_degrees(self) -> np.ndarray:
        return np.asarray(self.spec.theta1_degrees)

    @property
    def theta2_axis_degrees(self) -> np.ndarray:
        return np.asarray(self.spec.theta2_degrees)

    @property
    def values(self) -> np.ndarray:
        return np.asarray(
            [
                [
                    np.nan
                    if cell.finite_time_stretching_rate is None
                    else cell.finite_time_stretching_rate
                    for cell in row
                ]
                for row in self.cells
            ]
        )

    @property
    def statuses(self) -> np.ndarray:
        return np.asarray(
            [[cell.status.value for cell in row] for row in self.cells]
        )

    @property
    def valid_mask(self) -> np.ndarray:
        return np.asarray(
            [[cell.numerically_valid for cell in row] for row in self.cells]
        )

    @property
    def mean_seconds_per_cell(self) -> float:
        return self.elapsed_seconds / self.cell_count


def run_theta1_theta2_grid(
    spec: Theta1Theta2GridSpec,
) -> Theta1Theta2GridResult:
    """Evaluate theta1 rows at each ordered initial theta2 coordinate.

    Array row ``i`` fixes ``theta2_axis_degrees[i]`` and array column ``j``
    fixes ``theta1_axis_degrees[j]``. The row runner carries forward the
    existing completed-valid, completed-invalid, and execution-error behavior.
    """

    rows: list[tuple[Theta1Theta2GridCell, ...]] = []
    grid_started = perf_counter()
    for theta2_index, theta2_degrees in enumerate(spec.theta2_degrees):
        row_initial_state = replace(
            spec.observable_spec.initial_state,
            theta2=math.radians(theta2_degrees),
        )
        row_observable_spec = replace(
            spec.observable_spec,
            initial_state=row_initial_state,
        )
        row = run_theta1_sweep(
            Theta1SweepSpec(
                theta1_degrees=spec.theta1_degrees,
                observable_spec=row_observable_spec,
            )
        )
        rows.append(
            tuple(
                Theta1Theta2GridCell(
                    theta2_index=theta2_index,
                    theta1_index=theta1_index,
                    theta2_degrees=theta2_degrees,
                    theta1_sample=sample,
                )
                for theta1_index, sample in enumerate(row.samples)
            )
        )

    return Theta1Theta2GridResult(
        spec=spec,
        cells=tuple(rows),
        elapsed_seconds=perf_counter() - grid_started,
    )


def _validate_axis(values: tuple[float, ...], label: str) -> None:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or len(array) < 2 or not np.all(np.isfinite(array)):
        raise ValueError(f"{label} must contain at least two finite coordinates.")
    if np.any(np.diff(array) <= 0.0):
        raise ValueError(f"{label} must be strictly increasing.")
