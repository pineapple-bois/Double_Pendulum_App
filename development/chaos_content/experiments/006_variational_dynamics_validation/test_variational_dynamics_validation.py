"""Experiment-local tests for direct Euler–Lagrange variational dynamics."""

from __future__ import annotations

import math
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

EXPERIMENT_ROOT = Path(__file__).resolve().parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

import variational_dynamics_validation as experiment


@pytest.fixture(scope="module")
def dynamics():
    return experiment.VariationalDynamics()


def test_symbolic_flow_matches_actual_production_rhs(dynamics) -> None:
    production = experiment.DoublePendulumLagrangian(
        experiment.PARAMETERS,
        experiment.BASE_STATE_DEGREES,
        [0.0, 1.0e-6, 2],
        model=experiment.MODEL,
        solver_policy=experiment.SIMPLE_REFERENCE_SOLVER_POLICY,
    )
    for state, time_value in (
        (np.array([0.73, -1.21, 2.4, -3.1]), 0.37),
        (experiment.BASE_STATE_RADIANS, 0.0),
    ):
        np.testing.assert_allclose(
            dynamics.flow(state, time_value),
            np.asarray(production._system(state, time_value), dtype=float),
            rtol=0.0,
            atol=1.0e-13,
        )


def test_jacobian_matches_independent_directional_finite_difference(dynamics) -> None:
    state = np.array([0.73, -1.21, 2.4, -3.1])
    direction = np.array([0.3, -0.4, 0.5, -0.7])
    direction /= np.linalg.norm(direction)
    time_value = 0.37
    h_value = experiment.JACOBIAN_ASSESSMENT_H
    expected = dynamics.jacobian(state, time_value) @ direction
    actual = (
        dynamics.flow(state + h_value * direction, time_value)
        - dynamics.flow(state, time_value)
    ) / h_value
    relative_error = np.linalg.norm(actual - expected) / np.linalg.norm(expected)

    assert relative_error <= experiment.MAX_JACOBIAN_DIRECTIONAL_RELATIVE_ERROR


def test_flow_and_jacobian_are_periodic_under_independent_turn_shifts(dynamics) -> None:
    state = np.array([math.pi - 1.0e-8, -math.pi + 2.0e-8, 2.0, -3.0])
    expected_flow = dynamics.flow(state, 0.37)
    expected_jacobian = dynamics.jacobian(state, 0.37)
    for turns in ((1, -1), (-7, 4), (23, -19)):
        shifted = np.array(state, copy=True)
        shifted[:2] += 2.0 * math.pi * np.asarray(turns)
        np.testing.assert_allclose(
            dynamics.flow(shifted, 0.37),
            expected_flow,
            rtol=0.0,
            atol=experiment.MAX_PERIODICITY_ABSOLUTE_ERROR,
        )
        np.testing.assert_allclose(
            dynamics.jacobian(shifted, 0.37),
            expected_jacobian,
            rtol=0.0,
            atol=experiment.MAX_PERIODICITY_ABSOLUTE_ERROR,
        )


def test_physical_observables_are_periodic_under_equivalent_angles() -> None:
    state = np.array([0.73, -1.21, 2.4, -3.1])
    shifted = np.array(state, copy=True)
    shifted[:2] += 2.0 * math.pi * np.array([-11, 8])

    np.testing.assert_allclose(
        experiment.cartesian_full_state(shifted),
        experiment.cartesian_full_state(state),
        rtol=0.0,
        atol=1.0e-12,
    )
    np.testing.assert_allclose(
        experiment.simple_energy(shifted),
        experiment.simple_energy(state),
        rtol=0.0,
        atol=1.0e-12,
    )


def test_augmented_rhs_is_flow_and_jacobian_vector_product(dynamics) -> None:
    state = np.array([0.73, -1.21, 2.4, -3.1])
    tangent = np.array([0.2, -0.4, 0.7, -0.3])
    augmented = np.concatenate((state, tangent))
    actual = dynamics.augmented_rhs(0.37, augmented)

    np.testing.assert_allclose(actual[:4], dynamics.flow(state, 0.37))
    np.testing.assert_allclose(
        actual[4:], dynamics.jacobian(state, 0.37) @ tangent
    )


def test_initial_tangent_is_unit_candidate_a_pure_theta2_direction() -> None:
    assert math.isclose(
        experiment.candidate_a_norm(experiment.INITIAL_TANGENT_PHYSICAL),
        1.0,
        rel_tol=0.0,
        abs_tol=0.0,
    )
    np.testing.assert_array_equal(
        experiment.normalized_scaled_direction(
            experiment.INITIAL_TANGENT_PHYSICAL
        ),
        [0.0, 1.0, 0.0, 0.0],
    )


def test_angular_chart_rebase_never_wraps_tangent_components() -> None:
    augmented = np.array(
        [
            math.pi + 2.0e-6,
            -math.pi - 3.0e-6,
            0.4,
            -0.2,
            9.0,
            -8.0,
            7.0,
            -6.0,
        ]
    )
    rebased = experiment.canonicalize_augmented_state(augmented)

    assert -math.pi < rebased[0] <= math.pi
    assert -math.pi < rebased[1] <= math.pi
    np.testing.assert_array_equal(rebased[2:4], augmented[2:4])
    np.testing.assert_array_equal(rebased[4:], augmented[4:])
    np.testing.assert_allclose(
        experiment.wrap_angle_difference(rebased[:2] - augmented[:2]),
        [0.0, 0.0],
    )


def test_finite_branch_difference_and_tangent_direction_keep_sign() -> None:
    reference = np.array([math.pi - 1.0e-7, -math.pi + 2.0e-7, 0.4, -0.2])
    nearby = np.array([-math.pi + 3.0e-7, math.pi - 5.0e-7, 0.4, -0.2])
    difference = experiment.wrapped_el_difference(reference, nearby)

    assert difference[0] > 0.0
    assert difference[1] < 0.0
    assert experiment.direction_cosine(
        np.array([1.0, 0.0, 0.0, 0.0]),
        np.array([-1.0, 0.0, 0.0, 0.0]),
    ) == -1.0


def test_explicit_max_step_is_forwarded_to_solver(monkeypatch) -> None:
    captured: dict[str, float] = {}
    requested = np.linspace(0.0, 0.25, 4)
    initial = np.array([0.2, -0.3, 0.4, -0.5])

    def fake_solve_ivp(*args, **kwargs):
        captured["max_step"] = kwargs["max_step"]
        return SimpleNamespace(
            success=True,
            status=0,
            message="ok",
            nfev=17,
            njev=0,
            nlu=0,
            t=np.array(kwargs["t_eval"], copy=True),
            y=np.repeat(initial[:, None], len(kwargs["t_eval"]), axis=1),
        )

    monkeypatch.setattr(experiment, "solve_ivp", fake_solve_ivp)
    result = experiment.solve_one_segment(
        lambda time_value, state: state,
        initial,
        requested,
        experiment.SIMPLE_REFERENCE_SOLVER_POLICY,
        max_step=0.0125,
    )

    assert result["accepted"]
    assert captured["max_step"] == 0.0125
    assert result["solver_status"]["max_step_seconds"] == 0.0125


def test_piecewise_grid_has_exact_declared_chart_boundaries() -> None:
    np.testing.assert_allclose(
        experiment.segment_boundaries(), [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.29]
    )
    time = experiment.output_time_grid()
    assert time[0] == 0.0
    assert time[-1] == experiment.LOCAL_COMPARISON_END
    assert len(time) == 130
