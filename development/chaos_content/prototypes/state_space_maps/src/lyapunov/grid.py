"""Small rectangular samples of the finite-time Lyapunov observable."""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import numpy as np

from ..state_space_fields import (
    PeriodicAngularDomain,
    RectangularCell,
    RectangularSamplingResult,
    SampleAxis,
    sample_rectangle,
)
from .evaluation import (
    RenormalizedTangentEvaluator,
    evaluate_renormalized_tangent_reference,
)
from .reference import RenormalizedTangentDiagnostics, RenormalizedTangentSpec


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

    @classmethod
    def from_periodic_domain(
        cls,
        domain: PeriodicAngularDomain,
        observable_spec: RenormalizedTangentSpec | None = None,
    ) -> Theta1Theta2GridSpec:
        """Express the full periodic domain through this degree-based sampler."""

        return cls(
            theta1_degrees=tuple(
                float(value) for value in np.rad2deg(domain.theta1_axis_radians)
            ),
            theta2_degrees=tuple(
                float(value) for value in np.rad2deg(domain.theta2_axis_radians)
            ),
            observable_spec=observable_spec or RenormalizedTangentSpec(),
        )

    @property
    def shape(self) -> tuple[int, int]:
        """Return ``(theta2_count, theta1_count)`` in stored-array order."""

        return (len(self.theta2_degrees), len(self.theta1_degrees))


@dataclass(frozen=True)
class Theta1Theta2GridResult:
    """A rectangular field stored as ``[theta2_index, theta1_index]``."""

    spec: Theta1Theta2GridSpec
    sampling: RectangularSamplingResult[RenormalizedTangentDiagnostics]

    @property
    def cells(
        self,
    ) -> tuple[tuple[RectangularCell[RenormalizedTangentDiagnostics], ...], ...]:
        return self.sampling.cells

    @property
    def shape(self) -> tuple[int, int]:
        return self.sampling.shape

    @property
    def cell_count(self) -> int:
        return self.sampling.cell_count

    @property
    def theta1_axis_degrees(self) -> np.ndarray:
        return np.asarray(self.sampling.x_axis.values)

    @property
    def theta2_axis_degrees(self) -> np.ndarray:
        return np.asarray(self.sampling.y_axis.values)

    @property
    def values(self) -> np.ndarray:
        return self.sampling.values

    @property
    def statuses(self) -> np.ndarray:
        return self.sampling.statuses

    @property
    def valid_mask(self) -> np.ndarray:
        return self.sampling.valid_mask

    @property
    def elapsed_seconds(self) -> float:
        return self.sampling.elapsed_seconds

    @property
    def mean_seconds_per_cell(self) -> float:
        return self.sampling.mean_seconds_per_cell


def run_theta1_theta2_grid(
    spec: Theta1Theta2GridSpec,
    evaluator: RenormalizedTangentEvaluator = evaluate_renormalized_tangent_reference,
) -> Theta1Theta2GridResult:
    """Evaluate one scalar-observable adapter on an ordered rectangle.

    Array row ``i`` fixes ``theta2_axis_degrees[i]`` and array column ``j``
    fixes ``theta1_axis_degrees[j]``. This strategy is independent of the 1-D
    sweep and shares only the evaluator/outcome boundary with it.
    """

    theta1_axis = SampleAxis("theta1", "degrees", spec.theta1_degrees)
    theta2_axis = SampleAxis("theta2", "degrees", spec.theta2_degrees)

    def evaluate(theta1_degrees: float, theta2_degrees: float):
        initial_state = replace(
            spec.observable_spec.initial_state,
            theta1=math.radians(theta1_degrees),
            theta2=math.radians(theta2_degrees),
        )
        observable_spec = replace(
            spec.observable_spec,
            initial_state=initial_state,
        )
        return evaluator(observable_spec)

    return Theta1Theta2GridResult(
        spec=spec,
        sampling=sample_rectangle(theta1_axis, theta2_axis, evaluate),
    )


def _validate_axis(values: tuple[float, ...], label: str) -> None:
    if len(values) < 2:
        raise ValueError(f"{label} must contain at least two finite coordinates.")
    try:
        SampleAxis(label.removesuffix("_degrees"), "degrees", values)
    except ValueError as error:
        if "strictly increasing" in str(error):
            raise ValueError(f"{label} must be strictly increasing.") from error
        raise
