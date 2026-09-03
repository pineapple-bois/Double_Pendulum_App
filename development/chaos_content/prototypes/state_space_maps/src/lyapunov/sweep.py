"""Small one-dimensional samples of the finite-time Lyapunov observable."""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import numpy as np

from ..state_space_fields import (
    LineSample,
    LineSamplingResult,
    SampleAxis,
    sample_line,
)
from .evaluation import (
    RenormalizedTangentEvaluator,
    evaluate_renormalized_tangent_reference,
)
from .reference import RenormalizedTangentDiagnostics, RenormalizedTangentSpec


@dataclass(frozen=True)
class Theta1SweepSpec:
    """One ordered family varying only the initial ``theta1`` coordinate."""

    theta1_degrees: tuple[float, ...]
    observable_spec: RenormalizedTangentSpec = field(
        default_factory=RenormalizedTangentSpec
    )

    def __post_init__(self) -> None:
        SampleAxis("theta1", "degrees", self.theta1_degrees)

    @property
    def coordinate_name(self) -> str:
        return "theta1"

    @property
    def coordinate_unit(self) -> str:
        return "degrees"


@dataclass(frozen=True)
class Theta1SweepResult:
    spec: Theta1SweepSpec
    sampling: LineSamplingResult[RenormalizedTangentDiagnostics]

    @property
    def samples(self) -> tuple[LineSample[RenormalizedTangentDiagnostics], ...]:
        return self.sampling.samples

    @property
    def sample_count(self) -> int:
        return self.sampling.axis.samples

    @property
    def theta1_degrees(self) -> np.ndarray:
        return np.asarray(self.sampling.axis.values)

    @property
    def finite_time_stretching_rates(self) -> np.ndarray:
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
    def mean_seconds_per_sample(self) -> float:
        return self.sampling.mean_seconds_per_sample


def run_theta1_sweep(
    spec: Theta1SweepSpec,
    evaluator: RenormalizedTangentEvaluator = evaluate_renormalized_tangent_reference,
) -> Theta1SweepResult:
    """Evaluate one scalar-observable adapter along ordered initial theta1.

    The evaluator owns numerical failure translation. Any exception that it
    does not deliberately translate propagates out of the sampling strategy.
    """

    axis = SampleAxis("theta1", "degrees", spec.theta1_degrees)

    def evaluate(theta1_degrees: float):
        sample_state = replace(
            spec.observable_spec.initial_state,
            theta1=math.radians(theta1_degrees),
        )
        sample_spec = replace(spec.observable_spec, initial_state=sample_state)
        return evaluator(sample_spec)

    return Theta1SweepResult(
        spec=spec,
        sampling=sample_line(axis, evaluate),
    )
