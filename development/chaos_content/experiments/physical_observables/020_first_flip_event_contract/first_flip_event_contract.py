"""Experiment 020 reference evaluator for first completed link revolution.

This module owns only the physical-observable experiment boundary.  It uses
the validated four-state Euler--Lagrange flow with continuous lifted angles
and SciPy terminal events.  It deliberately does not use the segmented
Lyapunov driver, angular rebasing, tangent/JVP evolution, or QR machinery.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import tempfile
from dataclasses import asdict, dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Sequence


RUNTIME_CACHE_ROOT = Path(tempfile.gettempdir()) / "double-pendulum-chaos-cache"
RUNTIME_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(RUNTIME_CACHE_ROOT / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(RUNTIME_CACHE_ROOT / "xdg"))

import numpy as np
from scipy.integrate import solve_ivp


EXPERIMENT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_ROOT.parents[4]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from development.chaos_content.prototypes.state_space_maps.src.lyapunov.reference import (
    EulerLagrangeDynamics,
    EulerLagrangeState,
    PendulumParameters,
    SolverSpec,
    simple_energy,
)


TAU = 2.0 * math.pi


class FirstFlipStatus(str, Enum):
    """Mutually exclusive outcomes of one bounded first-flip calculation."""

    EVENT_OBSERVED = "event_observed"
    RIGHT_CENSORED = "right_censored"
    SOLVER_FAILURE = "solver_failure"
    INVALID_INTEGRATION = "invalid_integration"


class EventAttribution(str, Enum):
    """Resolution of the arm/direction identity at the earliest event."""

    NOT_APPLICABLE = "not_applicable"
    UNIQUE = "unique"
    TIED = "tied"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, order=True)
class EventIdentity:
    """One signed completed-revolution surface."""

    arm: int
    direction: int

    def __post_init__(self) -> None:
        if self.arm not in (1, 2):
            raise ValueError("event arm must be 1 or 2")
        if self.direction not in (-1, 1):
            raise ValueError("event direction must be -1 or +1")

    @property
    def label(self) -> str:
        sign = "+" if self.direction > 0 else "-"
        return f"arm{self.arm}{sign}"


EVENT_IDENTITIES = (
    EventIdentity(1, -1),
    EventIdentity(1, +1),
    EventIdentity(2, -1),
    EventIdentity(2, +1),
)


@dataclass(frozen=True)
class EventSurfaceResidual:
    """Value of one event surface at the reported earliest event state."""

    identity: EventIdentity
    residual: float


@dataclass(frozen=True)
class FirstFlipResult:
    """Experiment-level result for one bounded physical trajectory."""

    status: FirstFlipStatus
    event_observed: bool
    censored: bool
    solver_success: bool
    numerically_valid: bool
    solver_message: str
    attribution: EventAttribution
    event_time_seconds: float | None
    dimensionless_event_time: float | None
    event_identities: tuple[EventIdentity, ...]
    winning_arm: int | None
    winning_direction: int | None
    event_state: tuple[float, float, float, float] | None
    event_surface_residuals: tuple[EventSurfaceResidual, ...]
    triggering_angular_velocities: tuple[float, ...]
    minimum_competing_surface_margin: float | None
    initial_state: tuple[float, float, float, float]
    observation_horizon_seconds: float
    integration_endpoint_seconds: float
    gravity_timescale_seconds: float
    reference_length_metres: float
    solver_method: str
    solver_rtol: float
    solver_atol: float
    effective_max_step_seconds: float | None
    rhs_evaluations: int
    jacobian_evaluations: int
    lu_decompositions: int
    accepted_point_count: int
    maximum_accepted_angular_increment: float
    initial_energy_joules: float
    event_energy_joules: float | None
    maximum_absolute_energy_error_joules: float
    maximum_normalized_energy_drift: float
    event_normalized_energy_drift: float | None
    wall_seconds: float
    raw_event_counts: tuple[int, int, int, int]
    validation_issues: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation for deterministic evidence."""

        return _json_compatible(asdict(self))


@dataclass(frozen=True)
class NamedTrajectory:
    """One small deterministic smoke/evidence trajectory."""

    name: str
    initial_angles_degrees: tuple[float, float]
    observation_horizon_seconds: float
    expected_identity: EventIdentity | None
    purpose: str

    def initial_state(self) -> EulerLagrangeState:
        return EulerLagrangeState.from_degrees(
            self.initial_angles_degrees[0],
            self.initial_angles_degrees[1],
            0.0,
            0.0,
        )


NAMED_TRAJECTORIES = (
    NamedTrajectory(
        name="stable_downward",
        initial_angles_degrees=(0.0, 0.0),
        observation_horizon_seconds=5.0,
        expected_identity=None,
        purpose="robust right-censored equilibrium reference",
    ),
    NamedTrajectory(
        name="arm1_positive",
        initial_angles_degrees=(-150.0, -150.0),
        observation_horizon_seconds=5.0,
        expected_identity=EventIdentity(1, +1),
        purpose="positive completed revolution of arm 1",
    ),
    NamedTrajectory(
        name="arm1_negative",
        initial_angles_degrees=(150.0, 150.0),
        observation_horizon_seconds=5.0,
        expected_identity=EventIdentity(1, -1),
        purpose="negative completed revolution of arm 1",
    ),
    NamedTrajectory(
        name="arm2_positive",
        initial_angles_degrees=(179.0, 179.0),
        observation_horizon_seconds=5.0,
        expected_identity=EventIdentity(2, +1),
        purpose="positive completed revolution of arm 2",
    ),
    NamedTrajectory(
        name="arm2_negative",
        initial_angles_degrees=(-179.0, -179.0),
        observation_horizon_seconds=5.0,
        expected_identity=EventIdentity(2, -1),
        purpose="negative completed revolution of arm 2",
    ),
)


def gravity_timescale(parameters: PendulumParameters) -> float:
    """Return the accepted equal-link gravitational time scale."""

    if parameters.length1 != parameters.length2:
        raise ValueError(
            "Experiment 020 defines its dimensionless time only for equal link lengths."
        )
    return math.sqrt(parameters.length1 / parameters.gravity)


def default_solver_spec(parameters: PendulumParameters) -> SolverSpec:
    """Return the experiment's reference starting policy, pending validation."""

    return SolverSpec(max_step=gravity_timescale(parameters) / 32.0)


def energy_scale(parameters: PendulumParameters) -> float:
    """Return the existing parameter-based energy scale in joules."""

    return parameters.gravity * (
        (parameters.mass1 + parameters.mass2) * parameters.length1
        + parameters.mass2 * parameters.length2
    )


def first_flip_time(
    initial_state: EulerLagrangeState | Sequence[float],
    parameters: PendulumParameters | None = None,
    solver_spec: SolverSpec | None = None,
    observation_horizon: float = 5.0,
) -> FirstFlipResult:
    """Measure the first completed link revolution before a finite horizon.

    Supplying no solver specification selects the Experiment 020 starting
    policy: DOP853 with the established reference tolerances and
    ``max_step = t_g / 32``.  Supplying ``SolverSpec(max_step=None)`` requests
    the uncapped adaptive comparison policy.

    A successful trajectory with no event is returned as right-censored.  It
    is never interpreted as a trajectory that can never flip.
    """

    parameters = parameters or PendulumParameters()
    time_scale = gravity_timescale(parameters)
    solver_spec = solver_spec or default_solver_spec(parameters)
    state0 = _initial_state_array(initial_state)
    horizon = float(observation_horizon)
    if not math.isfinite(horizon) or horizon <= 0.0:
        raise ValueError("observation_horizon must be positive and finite")

    dynamics = _cached_dynamics(parameters)
    event_functions = _event_functions(state0)
    solver_arguments: dict[str, Any] = {
        "fun": dynamics.flow,
        "t_span": (0.0, horizon),
        "y0": state0,
        "method": solver_spec.method,
        "rtol": solver_spec.rtol,
        "atol": solver_spec.atol,
        "events": event_functions,
    }
    if solver_spec.max_step is not None:
        solver_arguments["max_step"] = solver_spec.max_step

    started = perf_counter()
    solution = solve_ivp(**solver_arguments)
    wall_seconds = perf_counter() - started

    times = np.asarray(solution.t, dtype=float)
    states = np.asarray(solution.y.T, dtype=float)
    integration_endpoint = float(times[-1]) if times.size else 0.0
    validation_issues = _structural_validation_issues(
        solution_success=bool(solution.success),
        times=times,
        states=states,
        horizon=horizon,
        event_lists=solution.t_events,
    )

    finite_states = states.shape[1:] == (4,) and np.all(np.isfinite(states))
    diagnostic_states = states if finite_states and len(states) else state0.reshape(1, 4)
    energies = np.asarray(simple_energy(diagnostic_states, parameters), dtype=float)
    initial_energy = float(simple_energy(state0, parameters))
    energy_errors = np.abs(energies - initial_energy)
    max_absolute_energy_error = float(np.max(energy_errors))
    max_normalized_energy_drift = max_absolute_energy_error / energy_scale(parameters)
    max_angular_increment = _maximum_angular_increment(diagnostic_states)

    records = _event_records(solution.t_events, solution.y_events)
    event_observed = bool(records)
    event_time: float | None = None
    dimensionless_time: float | None = None
    event_identities: tuple[EventIdentity, ...] = ()
    event_state: tuple[float, float, float, float] | None = None
    residuals: tuple[EventSurfaceResidual, ...] = ()
    triggering_velocities: tuple[float, ...] = ()
    competing_margin: float | None = None
    event_energy: float | None = None
    event_energy_drift: float | None = None
    attribution = EventAttribution.NOT_APPLICABLE
    winning_arm: int | None = None
    winning_direction: int | None = None

    if event_observed:
        event_time = min(record[0] for record in records)
        earliest_records = tuple(record for record in records if record[0] == event_time)
        event_identities = tuple(record[1] for record in earliest_records)
        selected_state = np.asarray(earliest_records[0][2], dtype=float)
        event_state = tuple(float(value) for value in selected_state)
        dimensionless_time = event_time / time_scale
        residuals = tuple(
            EventSurfaceResidual(
                identity=identity,
                residual=_surface_value(identity, selected_state, state0),
            )
            for identity in EVENT_IDENTITIES
        )
        triggering_velocities = tuple(
            float(selected_state[identity.arm + 1]) for identity in event_identities
        )
        competing_values = tuple(
            abs(item.residual)
            for item in residuals
            if item.identity not in event_identities
        )
        competing_margin = min(competing_values) if competing_values else None
        event_energy = float(simple_energy(selected_state, parameters))
        event_energy_drift = abs(event_energy - initial_energy) / energy_scale(parameters)
        if len(event_identities) == 1:
            attribution = EventAttribution.UNIQUE
            winning_arm = event_identities[0].arm
            winning_direction = event_identities[0].direction
        elif len(event_identities) > 1:
            attribution = EventAttribution.TIED
        else:
            attribution = EventAttribution.UNRESOLVED

    if not solution.success:
        status = FirstFlipStatus.SOLVER_FAILURE
    elif validation_issues:
        status = FirstFlipStatus.INVALID_INTEGRATION
    elif event_observed:
        status = FirstFlipStatus.EVENT_OBSERVED
    else:
        status = FirstFlipStatus.RIGHT_CENSORED

    censored = status is FirstFlipStatus.RIGHT_CENSORED
    numerically_valid = status in (
        FirstFlipStatus.EVENT_OBSERVED,
        FirstFlipStatus.RIGHT_CENSORED,
    )

    return FirstFlipResult(
        status=status,
        event_observed=event_observed,
        censored=censored,
        solver_success=bool(solution.success),
        numerically_valid=numerically_valid,
        solver_message=str(solution.message),
        attribution=attribution,
        event_time_seconds=event_time,
        dimensionless_event_time=dimensionless_time,
        event_identities=event_identities,
        winning_arm=winning_arm,
        winning_direction=winning_direction,
        event_state=event_state,
        event_surface_residuals=residuals,
        triggering_angular_velocities=triggering_velocities,
        minimum_competing_surface_margin=competing_margin,
        initial_state=tuple(float(value) for value in state0),
        observation_horizon_seconds=horizon,
        integration_endpoint_seconds=integration_endpoint,
        gravity_timescale_seconds=time_scale,
        reference_length_metres=parameters.length1,
        solver_method=solver_spec.method,
        solver_rtol=solver_spec.rtol,
        solver_atol=solver_spec.atol,
        effective_max_step_seconds=solver_spec.max_step,
        rhs_evaluations=int(solution.nfev),
        jacobian_evaluations=int(solution.njev),
        lu_decompositions=int(solution.nlu),
        accepted_point_count=len(times),
        maximum_accepted_angular_increment=max_angular_increment,
        initial_energy_joules=initial_energy,
        event_energy_joules=event_energy,
        maximum_absolute_energy_error_joules=max_absolute_energy_error,
        maximum_normalized_energy_drift=max_normalized_energy_drift,
        event_normalized_energy_drift=event_energy_drift,
        wall_seconds=wall_seconds,
        raw_event_counts=tuple(len(values) for values in solution.t_events),
        validation_issues=validation_issues,
    )


def run_named_trajectories(
    parameters: PendulumParameters | None = None,
    solver_spec: SolverSpec | None = None,
) -> tuple[tuple[NamedTrajectory, FirstFlipResult], ...]:
    """Run the bounded smoke/evidence suite without performing a map sweep."""

    parameters = parameters or PendulumParameters()
    solver_spec = solver_spec or default_solver_spec(parameters)
    return tuple(
        (
            case,
            first_flip_time(
                case.initial_state(),
                parameters=parameters,
                solver_spec=solver_spec,
                observation_horizon=case.observation_horizon_seconds,
            ),
        )
        for case in NAMED_TRAJECTORIES
    )


def named_suite_smoke_issues(
    observations: Sequence[tuple[NamedTrajectory, FirstFlipResult]],
) -> tuple[str, ...]:
    """Check only execution and declared identities, not scientific acceptance."""

    issues: list[str] = []
    for case, result in observations:
        if not result.solver_success or not result.numerically_valid:
            issues.append(f"{case.name}: invalid result status {result.status.value}")
            continue
        if case.expected_identity is None:
            if not result.censored:
                issues.append(f"{case.name}: expected right-censored result")
            continue
        if not result.event_observed:
            issues.append(f"{case.name}: expected an observed event")
            continue
        if result.event_identities != (case.expected_identity,):
            labels = ",".join(identity.label for identity in result.event_identities)
            issues.append(
                f"{case.name}: expected {case.expected_identity.label}, observed {labels or 'none'}"
            )
            continue
        triggering_residual = next(
            item.residual
            for item in result.event_surface_residuals
            if item.identity == case.expected_identity
        )
        smoke_limit = max(
            100.0 * result.solver_atol,
            256.0 * np.finfo(float).eps * TAU,
        )
        if abs(triggering_residual) > smoke_limit:
            issues.append(
                f"{case.name}: event residual {triggering_residual:.3e} "
                f"exceeds smoke limit {smoke_limit:.3e}"
            )
    return tuple(issues)


def _initial_state_array(
    initial_state: EulerLagrangeState | Sequence[float],
) -> np.ndarray:
    values = (
        initial_state.as_array()
        if isinstance(initial_state, EulerLagrangeState)
        else np.asarray(initial_state, dtype=float)
    )
    if values.shape != (4,) or not np.all(np.isfinite(values)):
        raise ValueError("initial_state must contain four finite components")
    return np.asarray(values, dtype=float)


@lru_cache(maxsize=16)
def _cached_dynamics(parameters: PendulumParameters) -> EulerLagrangeDynamics:
    return EulerLagrangeDynamics(parameters)


def _event_functions(
    initial_state: np.ndarray,
) -> tuple[Callable[[float, np.ndarray], float], ...]:
    initial_angles = np.asarray(initial_state[:2], dtype=float).copy()

    def make_event(identity: EventIdentity) -> Callable[[float, np.ndarray], float]:
        angle_index = identity.arm - 1

        def event(_time: float, state: np.ndarray) -> float:
            displacement = float(state[angle_index]) - float(initial_angles[angle_index])
            return identity.direction * displacement - TAU

        event.terminal = True  # type: ignore[attr-defined]
        event.direction = 1.0  # type: ignore[attr-defined]
        return event

    return tuple(make_event(identity) for identity in EVENT_IDENTITIES)


def _surface_value(
    identity: EventIdentity,
    state: np.ndarray,
    initial_state: np.ndarray,
) -> float:
    angle_index = identity.arm - 1
    displacement = float(state[angle_index]) - float(initial_state[angle_index])
    return identity.direction * displacement - TAU


def _event_records(
    event_times: Sequence[np.ndarray],
    event_states: Sequence[np.ndarray],
) -> tuple[tuple[float, EventIdentity, np.ndarray], ...]:
    records: list[tuple[float, EventIdentity, np.ndarray]] = []
    for identity, times, states in zip(
        EVENT_IDENTITIES, event_times, event_states, strict=True
    ):
        for time_value, state in zip(times, states, strict=True):
            records.append(
                (float(time_value), identity, np.asarray(state, dtype=float).copy())
            )
    return tuple(sorted(records, key=lambda record: (record[0], record[1])))


def _structural_validation_issues(
    *,
    solution_success: bool,
    times: np.ndarray,
    states: np.ndarray,
    horizon: float,
    event_lists: Sequence[np.ndarray],
) -> tuple[str, ...]:
    issues: list[str] = []
    if times.ndim != 1 or times.size == 0 or not np.all(np.isfinite(times)):
        issues.append("invalid_solver_time")
    if states.ndim != 2 or states.shape != (len(times), 4):
        issues.append("invalid_solver_state_shape")
    elif not np.all(np.isfinite(states)):
        issues.append("non_finite_solver_state")
    if not solution_success:
        return tuple(issues)
    event_observed = any(len(values) for values in event_lists)
    if not event_observed and times.size:
        endpoint_allowance = 256.0 * np.finfo(float).eps * max(1.0, horizon)
        if not math.isclose(float(times[-1]), horizon, rel_tol=0.0, abs_tol=endpoint_allowance):
            issues.append("successful_censored_run_did_not_reach_horizon")
    return tuple(issues)


def _maximum_angular_increment(states: np.ndarray) -> float:
    if len(states) < 2:
        return 0.0
    return float(np.max(np.abs(np.diff(states[:, :2], axis=0))))


def _json_compatible(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _json_compatible(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_compatible(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def _format_named_table(
    observations: Sequence[tuple[NamedTrajectory, FirstFlipResult]],
) -> str:
    header = (
        "name                 initial angles / deg  status          event      "
        "tau / s       tau/t_g    |phi_hit|    omega_hit    max dE/Escale  nfev"
    )
    rows = [header, "-" * len(header)]
    for case, result in observations:
        event_label = (
            ",".join(identity.label for identity in result.event_identities)
            if result.event_identities
            else "-"
        )
        event_time = (
            f"{result.event_time_seconds:.9f}"
            if result.event_time_seconds is not None
            else "-"
        )
        dimensionless_time = (
            f"{result.dimensionless_event_time:.6f}"
            if result.dimensionless_event_time is not None
            else "-"
        )
        triggering_residual = (
            max(
                abs(item.residual)
                for item in result.event_surface_residuals
                if item.identity in result.event_identities
            )
            if result.event_identities
            else 0.0
        )
        triggering_velocity = (
            max(abs(value) for value in result.triggering_angular_velocities)
            if result.triggering_angular_velocities
            else 0.0
        )
        rows.append(
            f"{case.name:<20} "
            f"({case.initial_angles_degrees[0]:7.1f},{case.initial_angles_degrees[1]:7.1f})  "
            f"{result.status.value:<15} {event_label:<10} "
            f"{event_time:>11} {dimensionless_time:>10} "
            f"{triggering_residual:>11.3e} "
            f"{triggering_velocity:>12.6f} "
            f"{result.maximum_normalized_energy_drift:>13.3e} "
            f"{result.rhs_evaluations:>5}"
        )
    return "\n".join(rows)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the deterministic named results as JSON instead of a table",
    )
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="fail if the bounded named suite does not execute with its declared identities",
    )
    arguments = parser.parse_args(argv)

    observations = run_named_trajectories()
    issues = named_suite_smoke_issues(observations) if arguments.self_check else ()
    if arguments.json:
        payload = {
            "experiment": "020_first_flip_event_contract",
            "scope": "implementation_smoke_evidence_not_full_validation",
            "cases": [
                {
                    "name": case.name,
                    "initial_angles_degrees": list(case.initial_angles_degrees),
                    "purpose": case.purpose,
                    "expected_identity": (
                        asdict(case.expected_identity)
                        if case.expected_identity is not None
                        else None
                    ),
                    "result": result.to_dict(),
                }
                for case, result in observations
            ],
            "self_check_issues": list(issues),
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(_format_named_table(observations))
        if arguments.self_check:
            print("\nself-check: " + ("PASS" if not issues else "FAIL"))
            for issue in issues:
                print(f"- {issue}")
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
