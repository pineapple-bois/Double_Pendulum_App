"""Experiment-local checks for the explicit distance conventions."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

EXPERIMENT_ROOT = Path(__file__).resolve().parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

import lyapunov_distance_investigation as experiment


def test_wrap_uses_requested_half_open_interval() -> None:
    actual = experiment.wrap_angle_difference(
        np.array([-math.pi, math.pi, -3.0 * math.pi, 3.0 * math.pi])
    )
    np.testing.assert_array_equal(actual, np.full(4, math.pi))


def test_equivalent_angles_across_boundary_have_zero_distance() -> None:
    reference = np.deg2rad(np.array([[179.0, -179.0, 0.0, 0.0]]))
    nearby = np.deg2rad(np.array([[-181.0, 181.0, 0.0, 0.0]]))
    difference = experiment.wrapped_el_difference(reference, nearby)

    np.testing.assert_allclose(difference, 0.0, atol=1.0e-14)
    np.testing.assert_allclose(experiment.candidate_a_distance(difference), 0.0)
    np.testing.assert_allclose(
        experiment.candidate_b_distance(reference, nearby), 0.0, atol=1.0e-14
    )


def test_cartesian_velocity_conversion() -> None:
    state = np.array([[0.0, 0.0, 1.0, 2.0]])
    expected = np.array([[0.0, -1.0, 0.0, -2.0, 1.0, 0.0, 3.0, 0.0]])
    np.testing.assert_allclose(experiment.cartesian_full_state(state), expected)


def test_initial_distance_and_nondimensional_scaling() -> None:
    epsilon = 1.0e-5
    reference = experiment.BASE_INITIAL_STATE_RADIANS.reshape(1, 4)
    nearby = np.array(reference, copy=True)
    nearby[0, 1] += epsilon
    difference = experiment.wrapped_el_difference(reference, nearby)

    expected_bob = 2.0 * math.sin(epsilon / 2.0)
    np.testing.assert_allclose(
        experiment.candidate_a_distance(difference), epsilon, rtol=0.0, atol=2.0e-12
    )
    np.testing.assert_allclose(
        experiment.candidate_b_distance(reference, nearby),
        expected_bob / experiment.CHARACTERISTIC_LENGTH_METRES,
        rtol=0.0,
        atol=2.0e-12,
    )
    np.testing.assert_allclose(
        experiment.second_bob_distance(reference, nearby),
        expected_bob,
        rtol=0.0,
        atol=2.0e-12,
    )
    assert math.isclose(
        experiment.characteristic_time(1.0), math.sqrt(1.0 / 9.81)
    )
