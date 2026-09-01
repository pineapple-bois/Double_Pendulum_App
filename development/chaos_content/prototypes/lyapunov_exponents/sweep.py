"""Small one-dimensional sweeps of the trusted finite-time observable."""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from enum import Enum
from time import perf_counter

import numpy as np

if __package__:
    from .reference import (
        EulerLagrangeState,
        RenormalizedTangentSpec,
        run_renormalized_tangent,
    )
else:
    from reference import (
        EulerLagrangeState,
        RenormalizedTangentSpec,
        run_renormalized_tangent,
    )


class SweepSampleStatus(str, Enum):
    """Outcome categories retained independently for every sample."""

    COMPLETED_VALID = "completed_valid"
    COMPLETED_INVALID = "completed_invalid"
    EXECUTION_ERROR = "execution_error"


@dataclass(frozen=True)
class Theta1SweepSpec:
    """One ordered family varying only the initial ``theta1`` coordinate."""

    theta1_degrees: tuple[float, ...]
    observable_spec: RenormalizedTangentSpec = field(
        default_factory=RenormalizedTangentSpec
    )

    def __post_init__(self) -> None:
        values = np.asarray(self.theta1_degrees, dtype=float)
        if values.ndim != 1 or len(values) == 0 or not np.all(np.isfinite(values)):
            raise ValueError("theta1_degrees must be a non-empty finite sequence.")
        if np.any(np.diff(values) <= 0.0):
            raise ValueError("theta1_degrees must be strictly increasing.")

    @property
    def coordinate_name(self) -> str:
        return "theta1"

    @property
    def coordinate_unit(self) -> str:
        return "degrees"


@dataclass(frozen=True)
class Theta1SweepSample:
    index: int
    theta1_degrees: float
    initial_state: EulerLagrangeState
    status: SweepSampleStatus
    finite_time_stretching_rate: float | None
    elapsed_seconds: float
    maximum_normalized_reference_energy_drift: float | None
    maximum_post_renormalization_norm_error: float | None
    solver_function_evaluations: int | None
    validity_issues: tuple[str, ...]
    error_type: str | None = None
    error_message: str | None = None

    @property
    def completed(self) -> bool:
        return self.status is not SweepSampleStatus.EXECUTION_ERROR

    @property
    def numerically_valid(self) -> bool:
        return self.status is SweepSampleStatus.COMPLETED_VALID


@dataclass(frozen=True)
class Theta1SweepResult:
    spec: Theta1SweepSpec
    samples: tuple[Theta1SweepSample, ...]
    elapsed_seconds: float

    @property
    def sample_count(self) -> int:
        return len(self.samples)

    @property
    def theta1_degrees(self) -> np.ndarray:
        return np.asarray([sample.theta1_degrees for sample in self.samples])

    @property
    def finite_time_stretching_rates(self) -> np.ndarray:
        return np.asarray(
            [
                np.nan
                if sample.finite_time_stretching_rate is None
                else sample.finite_time_stretching_rate
                for sample in self.samples
            ]
        )

    @property
    def valid_mask(self) -> np.ndarray:
        return np.asarray([sample.numerically_valid for sample in self.samples])

    @property
    def mean_seconds_per_sample(self) -> float:
        return self.elapsed_seconds / self.sample_count


def run_theta1_sweep(spec: Theta1SweepSpec) -> Theta1SweepResult:
    """Evaluate the trusted scalar while changing only initial ``theta1``.

    Expected numerical ``RuntimeError`` failures are retained per sample.
    Other exceptions propagate because they indicate a programming or
    specification defect rather than a failed numerical evaluation.
    """

    samples: list[Theta1SweepSample] = []
    sweep_started = perf_counter()
    for index, theta1_degrees in enumerate(spec.theta1_degrees):
        sample_state = replace(
            spec.observable_spec.initial_state,
            theta1=math.radians(theta1_degrees),
        )
        sample_spec = replace(spec.observable_spec, initial_state=sample_state)
        sample_started = perf_counter()
        try:
            observable = run_renormalized_tangent(sample_spec)
        except RuntimeError as error:
            samples.append(
                Theta1SweepSample(
                    index=index,
                    theta1_degrees=theta1_degrees,
                    initial_state=sample_state,
                    status=SweepSampleStatus.EXECUTION_ERROR,
                    finite_time_stretching_rate=None,
                    elapsed_seconds=perf_counter() - sample_started,
                    maximum_normalized_reference_energy_drift=None,
                    maximum_post_renormalization_norm_error=None,
                    solver_function_evaluations=None,
                    validity_issues=(),
                    error_type=type(error).__name__,
                    error_message=str(error),
                )
            )
            continue

        diagnostics = observable.diagnostics
        rate = observable.finite_time_stretching_rate
        finite_rate = math.isfinite(rate)
        validity_issues = list(diagnostics.validity_issues)
        if not finite_rate:
            validity_issues.append("finite-time stretching rate was non-finite")
        numerically_valid = diagnostics.numerically_valid and not validity_issues
        samples.append(
            Theta1SweepSample(
                index=index,
                theta1_degrees=theta1_degrees,
                initial_state=sample_state,
                status=(
                    SweepSampleStatus.COMPLETED_VALID
                    if numerically_valid
                    else SweepSampleStatus.COMPLETED_INVALID
                ),
                finite_time_stretching_rate=rate if finite_rate else None,
                elapsed_seconds=perf_counter() - sample_started,
                maximum_normalized_reference_energy_drift=(
                    diagnostics.maximum_normalized_reference_energy_drift
                ),
                maximum_post_renormalization_norm_error=(
                    diagnostics.maximum_post_renormalization_norm_error
                ),
                solver_function_evaluations=(
                    diagnostics.solver_function_evaluations
                ),
                validity_issues=tuple(validity_issues),
            )
        )

    return Theta1SweepResult(
        spec=spec,
        samples=tuple(samples),
        elapsed_seconds=perf_counter() - sweep_started,
    )
