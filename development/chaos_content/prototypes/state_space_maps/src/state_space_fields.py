"""Earned cross-observable contracts for reference state-space fields.

This module defines scalar-evaluation outcomes, explicit reference-sampling
shapes, and periodic angular coordinates. It does not know how any scientific
observable is calculated, stored, or rendered.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from numbers import Integral
from time import perf_counter
from typing import Callable, Generic, TypeVar

import numpy as np


DiagnosticsT = TypeVar("DiagnosticsT")


class EvaluationStatus(str, Enum):
    """Coordinate-neutral outcomes for one scalar-observable evaluation."""

    COMPLETED_VALID = "completed_valid"
    COMPLETED_INVALID = "completed_invalid"
    EXECUTION_ERROR = "execution_error"


@dataclass(frozen=True)
class ScalarEvaluation(Generic[DiagnosticsT]):
    """Outcome of evaluating one scalar observable at one domain point."""

    status: EvaluationStatus
    value: float | None
    diagnostics: DiagnosticsT | None
    elapsed_seconds: float
    evaluator: str
    validity_issues: tuple[str, ...] = ()
    error_type: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if not math.isfinite(self.elapsed_seconds) or self.elapsed_seconds < 0.0:
            raise ValueError("elapsed_seconds must be finite and nonnegative.")
        if not self.evaluator:
            raise ValueError("evaluator must identify the calculation path.")
        if self.value is not None and not math.isfinite(self.value):
            raise ValueError("A retained scalar value must be finite.")
        if self.status is EvaluationStatus.COMPLETED_VALID:
            if self.value is None or self.validity_issues:
                raise ValueError(
                    "A completed-valid evaluation needs a value and no validity issues."
                )
        elif self.status is EvaluationStatus.COMPLETED_INVALID:
            if not self.validity_issues:
                raise ValueError(
                    "A completed-invalid evaluation needs a declared validity issue."
                )
        elif self.status is EvaluationStatus.EXECUTION_ERROR:
            if self.value is not None or not self.error_type or not self.error_message:
                raise ValueError(
                    "An execution error needs error details and cannot retain a value."
                )
        if self.status is not EvaluationStatus.EXECUTION_ERROR and (
            self.error_type is not None or self.error_message is not None
        ):
            raise ValueError("Only execution-error evaluations may carry error details.")

    @property
    def completed(self) -> bool:
        return self.status is not EvaluationStatus.EXECUTION_ERROR

    @property
    def numerically_valid(self) -> bool:
        return self.status is EvaluationStatus.COMPLETED_VALID


@dataclass(frozen=True)
class SampleAxis:
    """One explicit ordered coordinate axis for reference sampling."""

    name: str
    unit: str
    values: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.name or not self.unit:
            raise ValueError("A sample axis needs a name and unit.")
        coordinates = np.asarray(self.values, dtype=float)
        if (
            coordinates.ndim != 1
            or len(coordinates) == 0
            or not np.all(np.isfinite(coordinates))
        ):
            raise ValueError("A sample axis needs a non-empty finite coordinate list.")
        if np.any(np.diff(coordinates) <= 0.0):
            raise ValueError("Sample-axis coordinates must be strictly increasing.")

    @property
    def samples(self) -> int:
        return len(self.values)


@dataclass(frozen=True)
class LineSample(Generic[DiagnosticsT]):
    index: int
    coordinate: float
    evaluation: ScalarEvaluation[DiagnosticsT]


@dataclass(frozen=True)
class LineSamplingResult(Generic[DiagnosticsT]):
    axis: SampleAxis
    samples: tuple[LineSample[DiagnosticsT], ...]
    elapsed_seconds: float

    @property
    def values(self) -> np.ndarray:
        return np.asarray(
            [
                np.nan if sample.evaluation.value is None else sample.evaluation.value
                for sample in self.samples
            ]
        )

    @property
    def statuses(self) -> np.ndarray:
        return np.asarray([sample.evaluation.status.value for sample in self.samples])

    @property
    def valid_mask(self) -> np.ndarray:
        return np.asarray(
            [sample.evaluation.numerically_valid for sample in self.samples]
        )

    @property
    def mean_seconds_per_sample(self) -> float:
        return self.elapsed_seconds / self.axis.samples


@dataclass(frozen=True)
class RectangularCell(Generic[DiagnosticsT]):
    y_index: int
    x_index: int
    y_coordinate: float
    x_coordinate: float
    evaluation: ScalarEvaluation[DiagnosticsT]


@dataclass(frozen=True)
class RectangularSamplingResult(Generic[DiagnosticsT]):
    """A reference field stored as ``[y_index, x_index]``."""

    x_axis: SampleAxis
    y_axis: SampleAxis
    cells: tuple[tuple[RectangularCell[DiagnosticsT], ...], ...]
    elapsed_seconds: float

    @property
    def shape(self) -> tuple[int, int]:
        return (self.y_axis.samples, self.x_axis.samples)

    @property
    def cell_count(self) -> int:
        return self.shape[0] * self.shape[1]

    @property
    def values(self) -> np.ndarray:
        return np.asarray(
            [
                [
                    np.nan if cell.evaluation.value is None else cell.evaluation.value
                    for cell in row
                ]
                for row in self.cells
            ]
        )

    @property
    def statuses(self) -> np.ndarray:
        return np.asarray(
            [[cell.evaluation.status.value for cell in row] for row in self.cells]
        )

    @property
    def valid_mask(self) -> np.ndarray:
        return np.asarray(
            [[cell.evaluation.numerically_valid for cell in row] for row in self.cells]
        )

    @property
    def mean_seconds_per_cell(self) -> float:
        return self.elapsed_seconds / self.cell_count


def sample_line(
    axis: SampleAxis,
    evaluator: Callable[[float], ScalarEvaluation[DiagnosticsT]],
) -> LineSamplingResult[DiagnosticsT]:
    """Evaluate one scalar adapter at each coordinate of one axis."""

    started = perf_counter()
    samples = tuple(
        LineSample(
            index=index,
            coordinate=coordinate,
            evaluation=evaluator(coordinate),
        )
        for index, coordinate in enumerate(axis.values)
    )
    return LineSamplingResult(
        axis=axis,
        samples=samples,
        elapsed_seconds=perf_counter() - started,
    )


def sample_rectangle(
    x_axis: SampleAxis,
    y_axis: SampleAxis,
    evaluator: Callable[[float, float], ScalarEvaluation[DiagnosticsT]],
) -> RectangularSamplingResult[DiagnosticsT]:
    """Evaluate one scalar adapter on explicit y rows and x columns."""

    started = perf_counter()
    rows = tuple(
        tuple(
            RectangularCell(
                y_index=y_index,
                x_index=x_index,
                y_coordinate=y_coordinate,
                x_coordinate=x_coordinate,
                evaluation=evaluator(x_coordinate, y_coordinate),
            )
            for x_index, x_coordinate in enumerate(x_axis.values)
        )
        for y_index, y_coordinate in enumerate(y_axis.values)
    )
    return RectangularSamplingResult(
        x_axis=x_axis,
        y_axis=y_axis,
        cells=rows,
        elapsed_seconds=perf_counter() - started,
    )


def full_periodic_angle_axis(samples: int) -> np.ndarray:
    """Return ``samples`` canonical angles spanning ``[-pi, pi)``.

    Coordinate ``k`` is ``-pi + 2*pi*k/samples`` for
    ``k = 0, ..., samples - 1``. The physically duplicate ``+pi`` endpoint is
    therefore never included.
    """

    count = _positive_sample_count(samples, "samples")
    return -math.pi + (2.0 * math.pi / count) * np.arange(count, dtype=float)


@dataclass(frozen=True)
class PeriodicAngularDomain:
    """Independent theta1/theta2 resolutions on the full angular torus."""

    theta1_samples: int
    theta2_samples: int

    def __post_init__(self) -> None:
        _positive_sample_count(self.theta1_samples, "theta1_samples")
        _positive_sample_count(self.theta2_samples, "theta2_samples")

    @classmethod
    def square(cls, samples_per_axis: int) -> PeriodicAngularDomain:
        count = _positive_sample_count(samples_per_axis, "samples_per_axis")
        return cls(theta1_samples=count, theta2_samples=count)

    @property
    def resolution(self) -> tuple[int, int]:
        """Return ``(theta1_samples, theta2_samples)``."""

        return (self.theta1_samples, self.theta2_samples)

    @property
    def field_shape(self) -> tuple[int, int]:
        """Return array shape ``(theta2_samples, theta1_samples)``."""

        return (self.theta2_samples, self.theta1_samples)

    @property
    def theta1_axis_radians(self) -> np.ndarray:
        return full_periodic_angle_axis(self.theta1_samples)

    @property
    def theta2_axis_radians(self) -> np.ndarray:
        return full_periodic_angle_axis(self.theta2_samples)


def _positive_sample_count(value: int, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or value <= 0:
        raise ValueError(f"{label} must be a positive integer sample count.")
    return int(value)
