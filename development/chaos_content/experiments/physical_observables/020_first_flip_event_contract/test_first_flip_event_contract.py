"""Focused scientific validation for Experiment 020's first-flip contract."""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import pytest
from scipy.integrate import solve_ivp
from scipy.optimize import brentq


EXPERIMENT_ROOT = Path(__file__).resolve().parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

from first_flip_event_contract import (
    EVENT_IDENTITIES,
    EventAttribution,
    EventIdentity,
    EulerLagrangeDynamics,
    EulerLagrangeState,
    FirstFlipResult,
    FirstFlipStatus,
    PendulumParameters,
    SolverSpec,
    default_solver_spec,
    first_flip_time,
    gravity_timescale,
)


# These gates were set after the validation matrix was inspected.  The worst
# observed time/state deviations from the stricter reference were 1.975e-8 s
# and 1.625e-7 respectively; the worst normalized energy drift was 1.340e-9.
EVENT_TIME_CONVERGENCE_ATOL = 5.0e-8
EVENT_STATE_CONVERGENCE_ATOL = 5.0e-7
ENERGY_DRIFT_LIMIT = 5.0e-9

# Solver event residuals were at most 1.776e-15.  This gate is ten times the
# baseline state atol and remains separate from any future near-tie policy.
EVENT_SURFACE_RESIDUAL_ATOL = 1.0e-10

# Lift/reflection discrepancies were below 8.7e-14 s and 7.3e-13 in state.
SYMMETRY_TIME_ATOL = 1.0e-10
SYMMETRY_STATE_ATOL = 1.0e-9

# The independent dense roots agreed to displayed floating-point precision.
DENSE_ROOT_TIME_ATOL = 1.0e-11
DENSE_ROOT_STATE_ATOL = 1.0e-10

HORIZON_BRACKET_SECONDS = 1.0e-6


EVENT_CASES = {
    "arm1_positive": ((-150.0, -150.0), EventIdentity(1, +1)),
    "arm1_negative": ((150.0, 150.0), EventIdentity(1, -1)),
    "arm2_positive": ((179.0, 179.0), EventIdentity(2, +1)),
    "arm2_negative": ((-179.0, -179.0), EventIdentity(2, -1)),
    "near_horizon": ((-180.0, -13.84615384615384), EventIdentity(2, -1)),
}


@dataclass(frozen=True)
class DenseRoot:
    """Independent dense-output root extracted without solve_ivp events."""

    identity: EventIdentity
    time: float
    state: np.ndarray
    residual: float
    bracket_width: float


@pytest.fixture(scope="module")
def parameters() -> PendulumParameters:
    return PendulumParameters()


@pytest.fixture(scope="module")
def policies(parameters: PendulumParameters) -> dict[str, SolverSpec]:
    time_scale = gravity_timescale(parameters)
    return {
        "baseline": SolverSpec(
            rtol=1.0e-9,
            atol=1.0e-11,
            max_step=time_scale / 32.0,
        ),
        "strict": SolverSpec(
            rtol=1.0e-11,
            atol=1.0e-13,
            max_step=time_scale / 32.0,
        ),
        "half_step": SolverSpec(
            rtol=1.0e-9,
            atol=1.0e-11,
            max_step=time_scale / 64.0,
        ),
        "uncapped": SolverSpec(
            rtol=1.0e-9,
            atol=1.0e-11,
            max_step=None,
        ),
    }


@pytest.fixture(scope="module")
def refinement_results(
    parameters: PendulumParameters,
    policies: dict[str, SolverSpec],
) -> dict[str, dict[str, FirstFlipResult]]:
    results: dict[str, dict[str, FirstFlipResult]] = {}
    for case_name, (angles, _identity) in EVENT_CASES.items():
        state = EulerLagrangeState.from_degrees(*angles, 0.0, 0.0)
        results[case_name] = {
            policy_name: first_flip_time(
                state,
                parameters=parameters,
                solver_spec=policy,
                observation_horizon=5.0,
            )
            for policy_name, policy in policies.items()
        }
    return results


@pytest.fixture(scope="module")
def bounded_screen(
    parameters: PendulumParameters,
) -> tuple[tuple[float, float, FirstFlipResult], ...]:
    """Bounded 13x13 search for a grazing or near-simultaneous candidate."""

    solver = default_solver_spec(parameters)
    angles = np.linspace(-180.0, 180.0, 13, endpoint=False)
    observations: list[tuple[float, float, FirstFlipResult]] = []
    for theta1 in angles:
        for theta2 in angles:
            result = first_flip_time(
                EulerLagrangeState.from_degrees(theta1, theta2, 0.0, 0.0),
                parameters=parameters,
                solver_spec=solver,
                observation_horizon=5.0,
            )
            observations.append((float(theta1), float(theta2), result))
    return tuple(observations)


def test_named_cases_cover_all_four_signed_event_surfaces(
    refinement_results: dict[str, dict[str, FirstFlipResult]],
) -> None:
    observed = set()
    for case_name, (_angles, expected_identity) in EVENT_CASES.items():
        result = refinement_results[case_name]["baseline"]
        assert result.status is FirstFlipStatus.EVENT_OBSERVED
        assert result.event_observed
        assert not result.censored
        assert result.attribution is EventAttribution.UNIQUE
        assert result.event_identities == (expected_identity,)
        assert result.winning_arm == expected_identity.arm
        assert result.winning_direction == expected_identity.direction
        assert result.event_time_seconds is not None
        assert result.dimensionless_event_time is not None
        assert result.event_state is not None
        assert result.triggering_angular_velocities
        assert result.validation_issues == ()
        observed.add(expected_identity)

        triggering_residual = _triggering_residual(result)
        assert abs(triggering_residual) <= EVENT_SURFACE_RESIDUAL_ATOL

    assert observed == set(EVENT_IDENTITIES)


def test_event_time_state_identity_and_energy_converge_under_refinement(
    refinement_results: dict[str, dict[str, FirstFlipResult]],
) -> None:
    for case_name, policy_results in refinement_results.items():
        strict = policy_results["strict"]
        assert strict.event_time_seconds is not None
        assert strict.event_state is not None
        expected_identity = EVENT_CASES[case_name][1]

        for result in policy_results.values():
            assert result.status is FirstFlipStatus.EVENT_OBSERVED
            assert result.event_identities == (expected_identity,)
            assert result.event_time_seconds is not None
            assert result.event_state is not None
            assert (
                abs(result.event_time_seconds - strict.event_time_seconds)
                <= EVENT_TIME_CONVERGENCE_ATOL
            )
            assert np.allclose(
                result.event_state,
                strict.event_state,
                rtol=0.0,
                atol=EVENT_STATE_CONVERGENCE_ATOL,
            )
            assert abs(_triggering_residual(result)) <= EVENT_SURFACE_RESIDUAL_ATOL
            assert result.maximum_normalized_energy_drift <= ENERGY_DRIFT_LIMIT
            assert result.maximum_accepted_angular_increment < 0.5


def test_dimensionless_time_uses_only_the_equal_link_scale(
    refinement_results: dict[str, dict[str, FirstFlipResult]],
    parameters: PendulumParameters,
) -> None:
    result = refinement_results["arm1_positive"]["baseline"]
    assert result.event_time_seconds is not None
    assert result.dimensionless_event_time is not None
    assert result.dimensionless_event_time == pytest.approx(
        result.event_time_seconds / gravity_timescale(parameters),
        rel=0.0,
        abs=2.0 * np.finfo(float).eps,
    )

    unequal = PendulumParameters(length1=1.0, length2=2.0)
    with pytest.raises(ValueError, match="equal link lengths"):
        gravity_timescale(unequal)
    with pytest.raises(ValueError, match="equal link lengths"):
        first_flip_time((0.0, 0.0, 0.0, 0.0), parameters=unequal)


def test_lift_invariance_for_individual_and_combined_two_pi_shifts(
    parameters: PendulumParameters,
) -> None:
    base_state = EulerLagrangeState.from_degrees(-150.0, -150.0, 0.0, 0.0).as_array()
    reference = first_flip_time(base_state, parameters=parameters)
    assert reference.event_state is not None
    assert reference.event_time_seconds is not None

    for k1, k2 in ((1, 0), (0, -1), (1, -1)):
        shifted_state = base_state + np.array((2.0 * math.pi * k1, 2.0 * math.pi * k2, 0.0, 0.0))
        shifted = first_flip_time(shifted_state, parameters=parameters)
        expected_event_state = np.asarray(reference.event_state) + np.array(
            (2.0 * math.pi * k1, 2.0 * math.pi * k2, 0.0, 0.0)
        )

        assert shifted.status is reference.status
        assert shifted.event_identities == reference.event_identities
        assert shifted.event_time_seconds is not None
        assert abs(shifted.event_time_seconds - reference.event_time_seconds) <= SYMMETRY_TIME_ATOL
        assert shifted.event_state is not None
        assert np.allclose(
            shifted.event_state,
            expected_event_state,
            rtol=0.0,
            atol=SYMMETRY_STATE_ATOL,
        )
        assert np.allclose(
            shifted.triggering_angular_velocities,
            reference.triggering_angular_velocities,
            rtol=0.0,
            atol=SYMMETRY_STATE_ATOL,
        )
        assert shifted.initial_energy_joules == pytest.approx(
            reference.initial_energy_joules,
            rel=0.0,
            abs=SYMMETRY_STATE_ATOL,
        )


@pytest.mark.parametrize(
    ("positive_case", "negative_case"),
    (("arm1_positive", "arm1_negative"), ("arm2_positive", "arm2_negative")),
)
def test_zero_velocity_reflection_symmetry_reverses_event_direction(
    refinement_results: dict[str, dict[str, FirstFlipResult]],
    positive_case: str,
    negative_case: str,
) -> None:
    positive = refinement_results[positive_case]["baseline"]
    negative = refinement_results[negative_case]["baseline"]
    assert positive.event_time_seconds is not None
    assert negative.event_time_seconds is not None
    assert positive.event_state is not None
    assert negative.event_state is not None

    assert abs(positive.event_time_seconds - negative.event_time_seconds) <= SYMMETRY_TIME_ATOL
    assert positive.winning_arm == negative.winning_arm
    assert positive.winning_direction == -negative.winning_direction
    assert np.allclose(
        positive.event_state,
        -np.asarray(negative.event_state),
        rtol=0.0,
        atol=SYMMETRY_STATE_ATOL,
    )
    assert np.allclose(
        positive.triggering_angular_velocities,
        -np.asarray(negative.triggering_angular_velocities),
        rtol=0.0,
        atol=SYMMETRY_STATE_ATOL,
    )
    assert positive.initial_energy_joules == pytest.approx(
        negative.initial_energy_joules,
        rel=0.0,
        abs=SYMMETRY_STATE_ATOL,
    )


def test_downward_equilibrium_is_stably_right_censored(
    parameters: PendulumParameters,
    policies: dict[str, SolverSpec],
) -> None:
    state = EulerLagrangeState.from_degrees(0.0, 0.0, 0.0, 0.0)
    for policy in policies.values():
        result = first_flip_time(
            state,
            parameters=parameters,
            solver_spec=policy,
            observation_horizon=5.0,
        )
        assert result.status is FirstFlipStatus.RIGHT_CENSORED
        assert result.censored
        assert not result.event_observed
        assert result.solver_success
        assert result.numerically_valid
        assert result.integration_endpoint_seconds == 5.0
        assert result.event_time_seconds is None
        assert result.dimensionless_event_time is None
        assert result.event_state is None
        assert result.event_identities == ()
        assert result.maximum_normalized_energy_drift == 0.0
        assert result.validation_issues == ()


def test_near_horizon_case_distinguishes_event_from_censoring(
    refinement_results: dict[str, dict[str, FirstFlipResult]],
    parameters: PendulumParameters,
    policies: dict[str, SolverSpec],
) -> None:
    reference = refinement_results["near_horizon"]["strict"]
    assert reference.event_time_seconds is not None
    state = EulerLagrangeState.from_degrees(
        *EVENT_CASES["near_horizon"][0],
        0.0,
        0.0,
    )
    event_time = reference.event_time_seconds

    below = first_flip_time(
        state,
        parameters=parameters,
        solver_spec=policies["strict"],
        observation_horizon=event_time - HORIZON_BRACKET_SECONDS,
    )
    above = first_flip_time(
        state,
        parameters=parameters,
        solver_spec=policies["strict"],
        observation_horizon=event_time + HORIZON_BRACKET_SECONDS,
    )
    at_reference_value = first_flip_time(
        state,
        parameters=parameters,
        solver_spec=policies["strict"],
        observation_horizon=event_time,
    )

    assert below.status is FirstFlipStatus.RIGHT_CENSORED
    assert below.integration_endpoint_seconds == pytest.approx(
        event_time - HORIZON_BRACKET_SECONDS,
        rel=0.0,
        abs=2.0e-14,
    )
    assert below.event_time_seconds is None
    assert above.status is FirstFlipStatus.EVENT_OBSERVED
    assert above.event_time_seconds == pytest.approx(
        event_time,
        rel=0.0,
        abs=EVENT_TIME_CONVERGENCE_ATOL,
    )

    # A horizon copied from a separate run is numerically ill-conditioned at
    # equality.  Either physical outcome is structurally valid here; README.md
    # records the observed censoring and the strict-cap recommendation.
    assert at_reference_value.status in (
        FirstFlipStatus.EVENT_OBSERVED,
        FirstFlipStatus.RIGHT_CENSORED,
    )
    assert at_reference_value.solver_success
    assert at_reference_value.numerically_valid


@pytest.mark.parametrize(
    ("angles", "expected_identity"),
    (((-150.0, -150.0), EventIdentity(1, +1)), ((179.0, 179.0), EventIdentity(2, +1))),
)
def test_independent_dense_output_root_matches_terminal_event(
    parameters: PendulumParameters,
    angles: tuple[float, float],
    expected_identity: EventIdentity,
) -> None:
    solver = SolverSpec(
        rtol=1.0e-11,
        atol=1.0e-13,
        max_step=gravity_timescale(parameters) / 64.0,
    )
    state = EulerLagrangeState.from_degrees(*angles, 0.0, 0.0).as_array()
    terminal = first_flip_time(
        state,
        parameters=parameters,
        solver_spec=solver,
        observation_horizon=3.0,
    )
    dense_roots = _independent_dense_roots(
        state,
        parameters=parameters,
        solver=solver,
        horizon=3.0,
    )

    assert dense_roots
    dense = dense_roots[0]
    assert dense.identity == expected_identity
    assert terminal.event_identities == (expected_identity,)
    assert terminal.event_time_seconds is not None
    assert terminal.event_state is not None
    assert abs(dense.time - terminal.event_time_seconds) <= DENSE_ROOT_TIME_ATOL
    assert np.allclose(
        dense.state,
        terminal.event_state,
        rtol=0.0,
        atol=DENSE_ROOT_STATE_ATOL,
    )
    assert abs(dense.residual) <= EVENT_SURFACE_RESIDUAL_ATOL
    requested_max_step = gravity_timescale(parameters) / 64.0
    floating_allowance = 64.0 * np.finfo(float).eps * max(1.0, requested_max_step)
    assert dense.bracket_width <= requested_max_step + floating_allowance


def test_bounded_search_finds_no_near_grazing_or_near_tie_candidate(
    bounded_screen: tuple[tuple[float, float, FirstFlipResult], ...],
) -> None:
    assert len(bounded_screen) == 13 * 13
    assert all(
        result.status in (FirstFlipStatus.EVENT_OBSERVED, FirstFlipStatus.RIGHT_CENSORED)
        for _theta1, _theta2, result in bounded_screen
    )
    event_results = [item for item in bounded_screen if item[2].event_observed]
    assert len(event_results) == 70

    minimum_crossing_speed = min(
        abs(result.triggering_angular_velocities[0])
        for _theta1, _theta2, result in event_results
    )
    minimum_competing_margin = min(
        result.minimum_competing_surface_margin
        for _theta1, _theta2, result in event_results
        if result.minimum_competing_surface_margin is not None
    )

    # The observed minima were 1.3298 rad/s and 1.5046 rad.  These screens do
    # not prove that pathological cases do not exist; they establish that this
    # bounded lattice supplied no useful candidate for either investigation.
    assert minimum_crossing_speed > 1.0
    assert minimum_competing_margin > 1.0


def test_bounded_search_extrema_remain_transversal_and_uniquely_separated(
    parameters: PendulumParameters,
    policies: dict[str, SolverSpec],
) -> None:
    screen_cases = {
        "smallest_crossing_speed": (
            (-152.30769230769232, 124.61538461538464),
            EventIdentity(1, +1),
        ),
        "smallest_competing_margin": (
            (152.30769230769232, 96.9230769230769),
            EventIdentity(2, -1),
        ),
    }

    for angles, expected_identity in screen_cases.values():
        results = [
            first_flip_time(
                EulerLagrangeState.from_degrees(*angles, 0.0, 0.0),
                parameters=parameters,
                solver_spec=policy,
                observation_horizon=5.0,
            )
            for policy in policies.values()
        ]
        strict = results[1]
        assert strict.event_time_seconds is not None
        for result in results:
            assert result.event_identities == (expected_identity,)
            assert result.event_time_seconds is not None
            assert abs(result.event_time_seconds - strict.event_time_seconds) <= EVENT_TIME_CONVERGENCE_ATOL
            assert abs(result.triggering_angular_velocities[0]) > 1.0
            assert result.minimum_competing_surface_margin is not None
            assert result.minimum_competing_surface_margin > 1.0
            assert result.maximum_normalized_energy_drift <= ENERGY_DRIFT_LIMIT

    grazing_state = EulerLagrangeState.from_degrees(
        -152.30769230769232,
        124.61538461538464,
        0.0,
        0.0,
    ).as_array()
    roots = _nonterminal_event_roots(
        grazing_state,
        parameters=parameters,
        solver=SolverSpec(
            rtol=1.0e-11,
            atol=1.0e-13,
            max_step=gravity_timescale(parameters) / 64.0,
        ),
        horizon=5.0,
    )
    assert roots[0][1] == EventIdentity(1, +1)
    assert roots[1][1] == EventIdentity(2, +1)
    assert roots[1][0] - roots[0][0] > 1.0


def _triggering_residual(result: FirstFlipResult) -> float:
    assert result.event_identities
    trigger = result.event_identities[0]
    return next(
        item.residual
        for item in result.event_surface_residuals
        if item.identity == trigger
    )


def _surface_value(
    identity: EventIdentity,
    state: np.ndarray,
    initial_state: np.ndarray,
) -> float:
    index = identity.arm - 1
    return identity.direction * (float(state[index]) - float(initial_state[index])) - 2.0 * math.pi


def _independent_dense_roots(
    initial_state: np.ndarray,
    *,
    parameters: PendulumParameters,
    solver: SolverSpec,
    horizon: float,
) -> tuple[DenseRoot, ...]:
    """Integrate without events, then bracket and refine every first surface root."""

    dynamics = EulerLagrangeDynamics(parameters)
    solver_arguments = {
        "fun": dynamics.flow,
        "t_span": (0.0, horizon),
        "y0": initial_state,
        "method": solver.method,
        "rtol": solver.rtol,
        "atol": solver.atol,
        "dense_output": True,
    }
    if solver.max_step is not None:
        solver_arguments["max_step"] = solver.max_step
    solution = solve_ivp(**solver_arguments)
    assert solution.success
    assert solution.sol is not None

    roots: list[DenseRoot] = []
    for identity in EVENT_IDENTITIES:
        samples = np.asarray(
            [
                _surface_value(identity, state, initial_state)
                for state in solution.y.T
            ]
        )
        crossing_indices = np.flatnonzero(
            (samples[:-1] < 0.0) & (samples[1:] >= 0.0)
        )
        if not len(crossing_indices):
            continue
        index = int(crossing_indices[0])
        left = float(solution.t[index])
        right = float(solution.t[index + 1])

        def dense_surface(time_value: float) -> float:
            return _surface_value(
                identity,
                np.asarray(solution.sol(time_value), dtype=float),
                initial_state,
            )

        root_time = brentq(
            dense_surface,
            left,
            right,
            xtol=5.0e-15,
            rtol=4.0 * np.finfo(float).eps,
        )
        root_state = np.asarray(solution.sol(root_time), dtype=float)
        roots.append(
            DenseRoot(
                identity=identity,
                time=root_time,
                state=root_state,
                residual=dense_surface(root_time),
                bracket_width=right - left,
            )
        )
    return tuple(sorted(roots, key=lambda root: (root.time, root.identity)))


def _nonterminal_event_roots(
    initial_state: np.ndarray,
    *,
    parameters: PendulumParameters,
    solver: SolverSpec,
    horizon: float,
) -> tuple[tuple[float, EventIdentity, float], ...]:
    """Return diagnostic roots without altering the ordinary terminal API."""

    dynamics = EulerLagrangeDynamics(parameters)
    events: list[Callable[[float, np.ndarray], float]] = []
    for identity in EVENT_IDENTITIES:

        def event(
            _time: float,
            state: np.ndarray,
            identity: EventIdentity = identity,
        ) -> float:
            return _surface_value(identity, state, initial_state)

        event.terminal = False  # type: ignore[attr-defined]
        event.direction = 1.0  # type: ignore[attr-defined]
        events.append(event)

    solver_arguments = {
        "fun": dynamics.flow,
        "t_span": (0.0, horizon),
        "y0": initial_state,
        "method": solver.method,
        "rtol": solver.rtol,
        "atol": solver.atol,
        "events": events,
    }
    if solver.max_step is not None:
        solver_arguments["max_step"] = solver.max_step
    solution = solve_ivp(**solver_arguments)
    assert solution.success

    roots: list[tuple[float, EventIdentity, float]] = []
    for identity, times, states in zip(
        EVENT_IDENTITIES,
        solution.t_events,
        solution.y_events,
        strict=True,
    ):
        for time_value, state in zip(times, states, strict=True):
            roots.append(
                (
                    float(time_value),
                    identity,
                    float(state[identity.arm + 1]),
                )
            )
    return tuple(sorted(roots, key=lambda root: (root[0], root[1])))
