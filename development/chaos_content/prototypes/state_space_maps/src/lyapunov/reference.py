"""Reusable numerical reference for the Sensitivity-to-Lyapunov story.

The module deliberately stays inside the Chaos prototype sandbox.  It derives
the Euler--Lagrange flow from the accepted production mechanics, but it has no
dependency on experiment modules or generated experiment outputs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import sympy as sp
from scipy.integrate import solve_ivp


import src.double_pendulum.models.lagrangian as lagrangian_module
from src.double_pendulum.math.functions import g, l1, l2, m1, m2
from src.double_pendulum.models import DoublePendulumLagrangian


STATE_ORDER = ("theta1", "theta2", "omega1", "omega2")


@dataclass(frozen=True)
class PendulumParameters:
    """SI parameters for the simple point-mass double pendulum."""

    length1: float = 1.0
    length2: float = 1.0
    mass1: float = 1.0
    mass2: float = 1.0
    gravity: float = 9.81

    def __post_init__(self) -> None:
        values = (
            self.length1,
            self.length2,
            self.mass1,
            self.mass2,
            self.gravity,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in values):
            raise ValueError("Pendulum parameters must be positive and finite.")

    def symbolic_substitutions(self) -> dict[sp.Expr, float]:
        return {
            l1: self.length1,
            l2: self.length2,
            m1: self.mass1,
            m2: self.mass2,
            g: self.gravity,
        }


@dataclass(frozen=True)
class EulerLagrangeState:
    """One physical state in ``(theta1, theta2, omega1, omega2)`` order."""

    theta1: float
    theta2: float
    omega1: float
    omega2: float

    def as_array(self) -> np.ndarray:
        values = np.asarray(
            (self.theta1, self.theta2, self.omega1, self.omega2), dtype=float
        )
        if not np.all(np.isfinite(values)):
            raise ValueError("Euler--Lagrange state components must be finite.")
        return values

    @classmethod
    def from_degrees(
        cls, theta1: float, theta2: float, omega1: float, omega2: float
    ) -> EulerLagrangeState:
        return cls(*np.deg2rad((theta1, theta2, omega1, omega2)))


@dataclass(frozen=True)
class SolverSpec:
    """Bounded DOP853 policy retained from Experiment 006."""

    method: str = "DOP853"
    rtol: float = 1.0e-9
    atol: float = 1.0e-11
    max_step: float | None = None

    def __post_init__(self) -> None:
        values = (self.rtol, self.atol)
        if not all(math.isfinite(value) and value > 0.0 for value in values):
            raise ValueError("Solver tolerances must be positive and finite.")
        if self.max_step is not None and (
            not math.isfinite(self.max_step) or self.max_step <= 0.0
        ):
            raise ValueError("An explicit max_step must be positive and finite.")


@dataclass(frozen=True)
class SensitivitySpec:
    """Specification for one finite-pair/direct-tangent comparison."""

    parameters: PendulumParameters = field(default_factory=PendulumParameters)
    initial_state: EulerLagrangeState = field(
        default_factory=lambda: EulerLagrangeState.from_degrees(179.0, 179.0, 0.0, 0.0)
    )
    finite_perturbation: tuple[float, float, float, float] = (
        0.0,
        1.0e-6,
        0.0,
        0.0,
    )
    duration: float = 1.29
    sampling_interval: float = 0.01
    chart_rebase_interval: float = 0.25
    local_distance_ceiling: float = 1.0e-2
    energy_drift_limit: float = 1.0e-7
    characteristic_length: float = 1.0
    solver: SolverSpec = field(default_factory=SolverSpec)

    def __post_init__(self) -> None:
        scalar_values = (
            self.duration,
            self.sampling_interval,
            self.chart_rebase_interval,
            self.local_distance_ceiling,
            self.energy_drift_limit,
            self.characteristic_length,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in scalar_values):
            raise ValueError("Workflow scales, intervals, and limits must be positive and finite.")
        perturbation = np.asarray(self.finite_perturbation, dtype=float)
        if perturbation.shape != (4,) or not np.all(np.isfinite(perturbation)):
            raise ValueError("finite_perturbation must contain four finite components.")
        if not np.any(perturbation):
            raise ValueError("finite_perturbation must be non-zero.")
        sample_steps = self.duration / self.sampling_interval
        rebase_steps = self.chart_rebase_interval / self.sampling_interval
        if not math.isclose(sample_steps, round(sample_steps), abs_tol=1.0e-12):
            raise ValueError("duration must be an integer multiple of sampling_interval.")
        if not math.isclose(rebase_steps, round(rebase_steps), abs_tol=1.0e-12):
            raise ValueError(
                "chart_rebase_interval must be an integer multiple of sampling_interval."
            )


@dataclass(frozen=True)
class RenormalizedTangentSpec:
    """Specification for one fixed-horizon, one-vector tangent calculation."""

    parameters: PendulumParameters = field(default_factory=PendulumParameters)
    initial_state: EulerLagrangeState = field(
        default_factory=lambda: EulerLagrangeState.from_degrees(179.0, 179.0, 0.0, 0.0)
    )
    initial_tangent: tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0)
    duration: float = 5.0
    renormalization_interval: float = 0.25
    sampling_interval: float = 0.01
    energy_drift_limit: float = 1.0e-7
    renormalization_norm_tolerance: float = 1.0e-12
    characteristic_length: float = 1.0
    solver: SolverSpec = field(default_factory=SolverSpec)

    def __post_init__(self) -> None:
        scalar_values = (
            self.duration,
            self.renormalization_interval,
            self.sampling_interval,
            self.energy_drift_limit,
            self.renormalization_norm_tolerance,
            self.characteristic_length,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in scalar_values):
            raise ValueError("Workflow scales, intervals, and limits must be positive and finite.")
        tangent = np.asarray(self.initial_tangent, dtype=float)
        if tangent.shape != (4,) or not np.all(np.isfinite(tangent)):
            raise ValueError("initial_tangent must contain four finite components.")
        if not np.any(tangent):
            raise ValueError("initial_tangent must be non-zero.")
        cycle_count = int(round(self.duration / self.renormalization_interval))
        if cycle_count <= 0 or not math.isclose(
            cycle_count * self.renormalization_interval,
            self.duration,
            rel_tol=0.0,
            abs_tol=1.0e-13,
        ):
            raise ValueError(
                "duration must contain an integer number of renormalization intervals."
            )


@dataclass(frozen=True)
class CandidateAMetric:
    """The accepted dimensionless Euler--Lagrange working geometry."""

    characteristic_length: float
    gravity: float

    @classmethod
    def from_spec(cls, spec: SensitivitySpec) -> CandidateAMetric:
        return cls(spec.characteristic_length, spec.parameters.gravity)

    @property
    def characteristic_time(self) -> float:
        return math.sqrt(self.characteristic_length / self.gravity)

    def scaling_matrix(self) -> np.ndarray:
        return np.diag((1.0, 1.0, self.characteristic_time, self.characteristic_time))

    def scale_tangent(self, tangent: np.ndarray) -> np.ndarray:
        tangent = _four_component_array(tangent, "tangent")
        scaled = np.array(tangent, copy=True)
        scaled[..., 2:] *= self.characteristic_time
        return scaled

    def tangent_norm(self, tangent: np.ndarray) -> np.ndarray:
        """Candidate-A norm for unwrapped infinitesimal components."""

        return np.linalg.norm(self.scale_tangent(tangent), axis=-1)

    def finite_difference(self, reference: np.ndarray, nearby: np.ndarray) -> np.ndarray:
        """Wrapped finite angles plus ordinary finite velocity differences."""

        reference = _four_component_array(reference, "reference state")
        nearby = _four_component_array(nearby, "nearby state")
        if reference.shape != nearby.shape:
            raise ValueError("Finite-state arrays must have identical shapes.")
        difference = nearby - reference
        result = np.array(difference, copy=True)
        result[..., :2] = wrap_angle_difference(difference[..., :2])
        return result

    def distance(self, reference: np.ndarray, nearby: np.ndarray) -> np.ndarray:
        return self.tangent_norm(self.finite_difference(reference, nearby))


@dataclass(frozen=True)
class Trajectory:
    time: np.ndarray
    state: np.ndarray
    second_bob_xy: np.ndarray


@dataclass(frozen=True)
class NearbyTrajectoryTrace:
    reference: Trajectory
    nearby: Trajectory
    finite_difference: np.ndarray
    second_bob_separation: np.ndarray
    candidate_a_separation: np.ndarray
    normalized_candidate_a_separation: np.ndarray
    normalized_scaled_difference: np.ndarray
    local_comparison_mask: np.ndarray

    @property
    def local_prefix_end_time(self) -> float:
        local_indices = np.flatnonzero(self.local_comparison_mask)
        return float(self.reference.time[local_indices[-1]]) if len(local_indices) else 0.0


@dataclass(frozen=True)
class TangentTrace:
    time: np.ndarray
    vector: np.ndarray
    candidate_a_norm: np.ndarray
    log_stretch: np.ndarray
    finite_time_rate: np.ndarray


@dataclass(frozen=True)
class NumericalDiagnostics:
    reference_max_normalized_energy_drift: float
    nearby_max_normalized_energy_drift: float
    max_step_seconds: float
    reference_segment_count: int
    nearby_segment_count: int


@dataclass(frozen=True)
class SensitivityToLyapunovResult:
    spec: SensitivitySpec
    metric: CandidateAMetric
    finite_pair: NearbyTrajectoryTrace
    tangent: TangentTrace
    finite_to_tangent_direction_cosine: np.ndarray
    diagnostics: NumericalDiagnostics


@dataclass(frozen=True)
class RenormalizedTangentDiagnostics:
    maximum_normalized_reference_energy_drift: float
    maximum_post_renormalization_norm_error: float
    max_step_seconds: float
    segment_count: int
    solver_function_evaluations: int
    numerically_valid: bool
    validity_issues: tuple[str, ...]


@dataclass(frozen=True)
class RenormalizedTangentResult:
    """One-vector Candidate-A stretching record over one declared horizon."""

    spec: RenormalizedTangentSpec
    metric: CandidateAMetric
    initial_unit_tangent: np.ndarray
    cycle_end_time: np.ndarray
    stretch_factor: np.ndarray
    log_stretch_increment: np.ndarray
    cumulative_log_stretch: np.ndarray
    cumulative_finite_time_rate: np.ndarray
    final_reference_state: np.ndarray
    final_unit_tangent: np.ndarray
    diagnostics: RenormalizedTangentDiagnostics

    @property
    def finite_time_stretching_rate(self) -> float:
        """Return the fixed-horizon scalar; no asymptotic limit is implied."""

        return float(self.cumulative_finite_time_rate[-1])


class EulerLagrangeDynamics:
    """Accepted simple-model EL flow and its exact symbolic state Jacobian."""

    def __init__(self, parameters: PendulumParameters) -> None:
        _, *equations = DoublePendulumLagrangian._compute_and_cache_equations("simple")
        substitutions = parameters.symbolic_substitutions()
        self.flow_expressions = tuple(expression.subs(substitutions) for expression in equations)
        self.state_symbols = (
            lagrangian_module.theta1,
            lagrangian_module.theta2,
            lagrangian_module.omega1,
            lagrangian_module.omega2,
        )
        self.time_symbol = lagrangian_module.t
        self.jacobian_expression = sp.Matrix(self.flow_expressions).jacobian(
            self.state_symbols
        )
        arguments = (*self.state_symbols, self.time_symbol)
        self._flow = sp.lambdify(arguments, self.flow_expressions, "numpy")
        self._jacobian = sp.lambdify(arguments, self.jacobian_expression, "numpy")

    def flow(self, time_value: float, state: np.ndarray) -> np.ndarray:
        state = _single_state(state)
        values = (*state, float(time_value))
        return np.asarray(self._flow(*values), dtype=float).reshape(4)

    def jacobian(self, time_value: float, state: np.ndarray) -> np.ndarray:
        state = _single_state(state)
        values = (*state, float(time_value))
        return np.asarray(self._jacobian(*values), dtype=float).reshape(4, 4)

    def reference_and_tangent_rhs(
        self, time_value: float, augmented: np.ndarray
    ) -> np.ndarray:
        augmented = np.asarray(augmented, dtype=float)
        if augmented.shape != (8,):
            raise ValueError("Augmented reference/tangent state must have eight components.")
        reference = augmented[:4]
        tangent = augmented[4:]
        return np.concatenate(
            (self.flow(time_value, reference), self.jacobian(time_value, reference) @ tangent)
        )


def wrap_angle_difference(values: np.ndarray) -> np.ndarray:
    """Map finite angular differences deterministically to ``(-pi, pi]``."""

    values = np.asarray(values, dtype=float)
    wrapped = np.remainder(values + math.pi, 2.0 * math.pi) - math.pi
    return np.where(wrapped == -math.pi, math.pi, wrapped)


def second_bob_position(state: np.ndarray, parameters: PendulumParameters) -> np.ndarray:
    state = _four_component_array(state, "state")
    theta1 = state[..., 0]
    theta2 = state[..., 1]
    x2 = parameters.length1 * np.sin(theta1) + parameters.length2 * np.sin(theta2)
    y2 = -parameters.length1 * np.cos(theta1) - parameters.length2 * np.cos(theta2)
    return np.stack((x2, y2), axis=-1)


def second_bob_separation(
    reference: np.ndarray, nearby: np.ndarray, parameters: PendulumParameters
) -> np.ndarray:
    displacement = second_bob_position(nearby, parameters) - second_bob_position(
        reference, parameters
    )
    return np.linalg.norm(displacement, axis=-1)


def simple_energy(state: np.ndarray, parameters: PendulumParameters) -> np.ndarray:
    state = _four_component_array(state, "state")
    theta1, theta2, omega1, omega2 = np.moveaxis(state, -1, 0)
    kinetic = (
        0.5 * (parameters.mass1 + parameters.mass2) * parameters.length1**2 * omega1**2
        + 0.5 * parameters.mass2 * parameters.length2**2 * omega2**2
        + parameters.mass2
        * parameters.length1
        * parameters.length2
        * omega1
        * omega2
        * np.cos(theta1 - theta2)
    )
    potential = -(
        (parameters.mass1 + parameters.mass2)
        * parameters.gravity
        * parameters.length1
        * np.cos(theta1)
        + parameters.mass2
        * parameters.gravity
        * parameters.length2
        * np.cos(theta2)
    )
    return np.asarray(kinetic + potential, dtype=float)


def normalized_energy_drift(
    state: np.ndarray, parameters: PendulumParameters
) -> np.ndarray:
    energy = simple_energy(state, parameters)
    return np.abs(energy - energy[0]) / _energy_scale(parameters)


def run_sensitivity_to_lyapunov(
    spec: SensitivitySpec | None = None,
) -> SensitivityToLyapunovResult:
    """Run the declared finite-pair and direct-tangent teaching workflow."""

    spec = spec or SensitivitySpec()
    metric = CandidateAMetric.from_spec(spec)
    dynamics = EulerLagrangeDynamics(spec.parameters)
    time = _time_grid(spec)
    finite_perturbation = np.asarray(spec.finite_perturbation, dtype=float)
    perturbation_norm = float(metric.tangent_norm(finite_perturbation))
    initial_tangent = finite_perturbation / perturbation_norm
    initial_reference = spec.initial_state.as_array()

    augmented_initial = np.concatenate((initial_reference, initial_tangent))
    augmented, reference_segments = _integrate_piecewise(
        dynamics.reference_and_tangent_rhs,
        augmented_initial,
        time,
        spec,
        tangent_components=True,
    )
    nearby_state, nearby_segments = _integrate_piecewise(
        dynamics.flow,
        initial_reference + finite_perturbation,
        time,
        spec,
        tangent_components=False,
    )

    reference_state = augmented[:, :4]
    tangent_vector = augmented[:, 4:]
    finite_difference = metric.finite_difference(reference_state, nearby_state)
    candidate_a_separation = metric.tangent_norm(finite_difference)
    normalized_scaled_difference = metric.scale_tangent(finite_difference) / perturbation_norm
    normalized_candidate_a_separation = np.linalg.norm(
        normalized_scaled_difference, axis=1
    )
    tangent_norm = metric.tangent_norm(tangent_vector)
    log_stretch = np.log(tangent_norm / tangent_norm[0])
    finite_time_rate = np.full_like(log_stretch, np.nan)
    finite_time_rate[1:] = log_stretch[1:] / time[1:]
    tangent_scaled_direction = metric.scale_tangent(tangent_vector) / tangent_norm[:, None]
    finite_direction = (
        normalized_scaled_difference / normalized_candidate_a_separation[:, None]
    )
    direction_cosine = np.sum(finite_direction * tangent_scaled_direction, axis=1)

    reference_drift = normalized_energy_drift(reference_state, spec.parameters)
    nearby_drift = normalized_energy_drift(nearby_state, spec.parameters)
    reference_max_drift = float(np.max(reference_drift))
    nearby_max_drift = float(np.max(nearby_drift))
    if reference_max_drift > spec.energy_drift_limit:
        raise RuntimeError(
            "Reference energy drift exceeded the declared workflow limit: "
            f"{reference_max_drift:.3e} > {spec.energy_drift_limit:.3e}."
        )
    if nearby_max_drift > spec.energy_drift_limit:
        raise RuntimeError(
            "Nearby energy drift exceeded the declared workflow limit: "
            f"{nearby_max_drift:.3e} > {spec.energy_drift_limit:.3e}."
        )

    reference = Trajectory(
        time=time,
        state=reference_state,
        second_bob_xy=second_bob_position(reference_state, spec.parameters),
    )
    nearby = Trajectory(
        time=time,
        state=nearby_state,
        second_bob_xy=second_bob_position(nearby_state, spec.parameters),
    )
    pair = NearbyTrajectoryTrace(
        reference=reference,
        nearby=nearby,
        finite_difference=finite_difference,
        second_bob_separation=second_bob_separation(
            reference_state, nearby_state, spec.parameters
        ),
        candidate_a_separation=candidate_a_separation,
        normalized_candidate_a_separation=normalized_candidate_a_separation,
        normalized_scaled_difference=normalized_scaled_difference,
        local_comparison_mask=candidate_a_separation <= spec.local_distance_ceiling,
    )
    tangent = TangentTrace(
        time=time,
        vector=tangent_vector,
        candidate_a_norm=tangent_norm,
        log_stretch=log_stretch,
        finite_time_rate=finite_time_rate,
    )
    diagnostics = NumericalDiagnostics(
        reference_max_normalized_energy_drift=reference_max_drift,
        nearby_max_normalized_energy_drift=nearby_max_drift,
        max_step_seconds=_resolved_max_step(spec),
        reference_segment_count=reference_segments,
        nearby_segment_count=nearby_segments,
    )
    return SensitivityToLyapunovResult(
        spec=spec,
        metric=metric,
        finite_pair=pair,
        tangent=tangent,
        finite_to_tangent_direction_cosine=direction_cosine,
        diagnostics=diagnostics,
    )


def run_renormalized_tangent(
    spec: RenormalizedTangentSpec | None = None,
) -> RenormalizedTangentResult:
    """Evaluate one fixed-horizon renormalized tangent stretching observable.

    The returned scalar is the signed accumulated Candidate-A logarithmic
    stretch divided by the declared duration.  It is a finite-time quantity,
    not an assertion of asymptotic convergence.
    """

    spec = spec or RenormalizedTangentSpec()
    dynamics = EulerLagrangeDynamics(spec.parameters)
    return _run_renormalized_tangent_with_rhs(
        spec,
        dynamics.reference_and_tangent_rhs,
    )


def _run_renormalized_tangent_with_rhs(
    spec: RenormalizedTangentSpec,
    reference_and_tangent_rhs: Callable[[float, np.ndarray], np.ndarray],
    *,
    segment_solver: Callable[..., tuple[np.ndarray, int]] | None = None,
) -> RenormalizedTangentResult:
    """Run the accepted observable with one validated augmented-state RHS."""

    solve_segment = _solve_segment if segment_solver is None else segment_solver
    metric = CandidateAMetric(spec.characteristic_length, spec.parameters.gravity)
    initial_tangent = np.asarray(spec.initial_tangent, dtype=float)
    initial_unit_tangent = initial_tangent / float(metric.tangent_norm(initial_tangent))
    scaling_matrix = metric.scaling_matrix()
    inverse_scaling_matrix = np.linalg.inv(scaling_matrix)
    reference = spec.initial_state.as_array()
    tangent = np.array(initial_unit_tangent, copy=True)
    initial_energy = float(simple_energy(reference, spec.parameters))
    cycle_count = int(round(spec.duration / spec.renormalization_interval))
    boundaries = np.linspace(0.0, spec.duration, cycle_count + 1)
    max_step = _resolved_interval_max_step(
        spec.solver,
        spec.characteristic_length,
        spec.parameters.gravity,
        spec.renormalization_interval,
    )

    stretch_factors: list[float] = []
    log_increments: list[float] = []
    cumulative_logs: list[float] = []
    cumulative_rates: list[float] = []
    maximum_energy_drift = 0.0
    maximum_norm_error = 0.0
    cumulative_log = 0.0
    function_evaluations = 0

    for start, end in zip(boundaries[:-1], boundaries[1:]):
        sample_count = max(
            2, int(round((end - start) / spec.sampling_interval)) + 1
        )
        requested = np.linspace(start, end, sample_count)
        augmented, nfev = solve_segment(
            reference_and_tangent_rhs,
            np.concatenate((reference, tangent)),
            requested,
            spec.solver,
            max_step,
        )
        function_evaluations += nfev
        reference_samples = augmented[:, :4]
        reference_raw = reference_samples[-1]
        tangent_pre = augmented[-1, 4:]
        scaled_pre = scaling_matrix @ tangent_pre
        stretch_factor = float(np.linalg.norm(scaled_pre))
        if not math.isfinite(stretch_factor) or stretch_factor <= 0.0:
            raise RuntimeError("Tangent stretch factor must remain positive and finite.")
        log_increment = math.log(stretch_factor)
        cumulative_log += log_increment
        tangent = inverse_scaling_matrix @ (scaled_pre / stretch_factor)
        post_norm_error = abs(float(metric.tangent_norm(tangent)) - 1.0)
        maximum_norm_error = max(maximum_norm_error, post_norm_error)
        reference = _rebase_reference_angles(
            reference_raw[None, :], tangent_components=False
        )[0]

        energy = simple_energy(reference_samples, spec.parameters)
        segment_energy_drift = float(
            np.max(np.abs(energy - initial_energy) / _energy_scale(spec.parameters))
        )
        maximum_energy_drift = max(maximum_energy_drift, segment_energy_drift)
        stretch_factors.append(stretch_factor)
        log_increments.append(log_increment)
        cumulative_logs.append(cumulative_log)
        cumulative_rates.append(cumulative_log / float(end))

    validity_issues: list[str] = []
    if maximum_energy_drift > spec.energy_drift_limit:
        validity_issues.append("reference energy drift exceeded its declared limit")
    if maximum_norm_error > spec.renormalization_norm_tolerance:
        validity_issues.append("post-renormalization Candidate-A norm error exceeded its limit")
    diagnostics = RenormalizedTangentDiagnostics(
        maximum_normalized_reference_energy_drift=maximum_energy_drift,
        maximum_post_renormalization_norm_error=maximum_norm_error,
        max_step_seconds=max_step,
        segment_count=cycle_count,
        solver_function_evaluations=function_evaluations,
        numerically_valid=not validity_issues,
        validity_issues=tuple(validity_issues),
    )
    return RenormalizedTangentResult(
        spec=spec,
        metric=metric,
        initial_unit_tangent=initial_unit_tangent,
        cycle_end_time=boundaries[1:],
        stretch_factor=np.asarray(stretch_factors),
        log_stretch_increment=np.asarray(log_increments),
        cumulative_log_stretch=np.asarray(cumulative_logs),
        cumulative_finite_time_rate=np.asarray(cumulative_rates),
        final_reference_state=reference,
        final_unit_tangent=tangent,
        diagnostics=diagnostics,
    )


def _time_grid(spec: SensitivitySpec) -> np.ndarray:
    sample_count = int(round(spec.duration / spec.sampling_interval)) + 1
    return np.linspace(0.0, spec.duration, sample_count)


def _segment_boundaries(spec: SensitivitySpec) -> np.ndarray:
    complete = int(math.floor(spec.duration / spec.chart_rebase_interval))
    boundaries = [index * spec.chart_rebase_interval for index in range(complete + 1)]
    if not math.isclose(boundaries[-1], spec.duration, abs_tol=1.0e-14):
        boundaries.append(spec.duration)
    return np.asarray(boundaries, dtype=float)


def _integrate_piecewise(
    rhs: Callable[[float, np.ndarray], np.ndarray],
    initial: np.ndarray,
    time: np.ndarray,
    spec: SensitivitySpec,
    *,
    tangent_components: bool,
) -> tuple[np.ndarray, int]:
    stored_segments: list[np.ndarray] = []
    current = np.asarray(initial, dtype=float)
    boundaries = _segment_boundaries(spec)
    max_step = _resolved_max_step(spec)
    for segment_index, (start, end) in enumerate(zip(boundaries[:-1], boundaries[1:])):
        mask = (time >= start - 1.0e-14) & (time <= end + 1.0e-14)
        requested = time[mask]
        state, _ = _solve_segment(rhs, current, requested, spec.solver, max_step)
        state = _rebase_reference_angles(state, tangent_components=tangent_components)
        current = state[-1]
        if segment_index:
            state = state[1:]
        stored_segments.append(state)
    combined = np.concatenate(stored_segments)
    if combined.shape[0] != len(time):
        raise RuntimeError("Piecewise integration did not reproduce the requested grid.")
    return combined, len(boundaries) - 1


def _resolved_max_step(spec: SensitivitySpec) -> float:
    return _resolved_interval_max_step(
        spec.solver,
        spec.characteristic_length,
        spec.parameters.gravity,
        spec.chart_rebase_interval,
    )


def _resolved_interval_max_step(
    solver: SolverSpec,
    characteristic_length: float,
    gravity: float,
    interval: float,
) -> float:
    if solver.max_step is not None:
        return solver.max_step
    characteristic_time = math.sqrt(characteristic_length / gravity)
    return min(
        characteristic_time / 32.0,
        interval / 25.0,
    )


def _solve_segment(
    rhs: Callable[[float, np.ndarray], np.ndarray],
    initial: np.ndarray,
    requested: np.ndarray,
    solver: SolverSpec,
    max_step: float,
) -> tuple[np.ndarray, int]:
    start = float(requested[0])
    end = float(requested[-1])
    result = solve_ivp(
        rhs,
        (start, end),
        initial,
        t_eval=requested,
        method=solver.method,
        rtol=solver.rtol,
        atol=solver.atol,
        max_step=max_step,
    )
    state = np.asarray(result.y.T, dtype=float)
    expected_shape = (len(requested), len(initial))
    if (
        not result.success
        or result.t.shape != requested.shape
        or not np.allclose(result.t, requested, rtol=0.0, atol=1.0e-13)
        or state.shape != expected_shape
        or not np.all(np.isfinite(state))
    ):
        raise RuntimeError(f"Integration failed on [{start}, {end}]: {result.message}")
    return state, int(result.nfev)


def _energy_scale(parameters: PendulumParameters) -> float:
    return parameters.gravity * (
        (parameters.mass1 + parameters.mass2) * parameters.length1
        + parameters.mass2 * parameters.length2
    )


def _rebase_reference_angles(
    state: np.ndarray, *, tangent_components: bool
) -> np.ndarray:
    expected_width = 8 if tangent_components else 4
    result = np.asarray(state, dtype=float).copy()
    if result.shape[-1] != expected_width:
        raise ValueError(f"Expected a state width of {expected_width}.")
    result[..., :2] = wrap_angle_difference(result[..., :2])
    return result


def _single_state(state: np.ndarray) -> np.ndarray:
    state = np.asarray(state, dtype=float)
    if state.shape != (4,) or not np.all(np.isfinite(state)):
        raise ValueError("Euler--Lagrange state must contain four finite components.")
    return state


def _four_component_array(values: np.ndarray, label: str) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if values.shape[-1:] != (4,) or not np.all(np.isfinite(values)):
        raise ValueError(f"{label} must end in four finite components.")
    return values
