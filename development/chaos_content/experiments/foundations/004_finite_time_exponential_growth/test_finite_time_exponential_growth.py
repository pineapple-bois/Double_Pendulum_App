"""Experiment-local tests for the finite-window inference rule."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

EXPERIMENT_ROOT = Path(__file__).resolve().parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

import finite_time_exponential_growth as experiment


def test_primary_and_audit_intervals_are_predeclared() -> None:
    assert experiment.primary_interval() == (0.32, 1.12)
    intervals = experiment.audit_intervals()
    assert len(intervals) == 11
    assert (0.32, 1.12) in intervals
    assert all(
        end - start + 1.0e-12
        >= experiment.MIN_DURATION_IN_TC * experiment.characteristic_time()
        for start, end in intervals
    )
    assert len(experiment.endpoint_neighbours(0.32, 1.12)) == 8


def test_linear_diagnostic_recovers_declared_finite_window_rate() -> None:
    time = np.linspace(0.0, 2.0, 201)
    values = 1.25 + 3.0 * time
    result = experiment.linear_diagnostic(time, values, 0.32, 1.12)

    assert result["valid"]
    assert math.isclose(result["endpoint_rate_per_second"], 3.0)
    assert math.isclose(result["fitted_slope_per_second"], 3.0)
    assert math.isclose(result["r_squared"], 1.0)
    assert result["max_abs_residual"] < 1.0e-12


def test_common_locality_stops_at_first_violation_without_reentry() -> None:
    time = np.array([0.0, 0.1, 0.2, 0.3])
    runs = {}
    for index, epsilon in enumerate(experiment.EPSILONS):
        distance = np.array([epsilon, 2 * epsilon, 3 * epsilon, 2 * epsilon])
        y = np.log(distance / distance[0]) + index * np.array([0.0, 0.0, 0.2, 0.0])
        runs[epsilon] = {"series": {"time": time, "distance_a": distance, "y_a": y}}

    locality = experiment.common_locality(runs)
    assert locality["end_time"] == 0.1
    assert locality["first_violation_time"] == 0.2
    assert locality["first_violation_reasons"] == ["perturbation_collapse_spread"]
    np.testing.assert_array_equal(locality["mask"], [True, True, False, False])


def test_wrapping_and_dimensionless_distances_match_experiment_003_conventions() -> None:
    epsilon = 1.0e-5
    reference = np.deg2rad(np.array([[179.0, 179.0, 0.0, 0.0]]))
    nearby = np.array(reference, copy=True)
    nearby[0, 1] += epsilon
    difference = experiment.wrapped_el_difference(reference, nearby)

    np.testing.assert_allclose(difference, [[0.0, epsilon, 0.0, 0.0]], atol=2.0e-12)
    np.testing.assert_allclose(
        experiment.candidate_a_distance(difference), epsilon, atol=2.0e-12
    )
    expected_cartesian = 2.0 * math.sin(epsilon / 2.0)
    np.testing.assert_allclose(
        experiment.candidate_b_distance(reference, nearby),
        expected_cartesian,
        atol=2.0e-12,
    )


def test_log_normalization_reports_zero_as_invalid_without_clipping() -> None:
    values, valid = experiment.positive_log_normalized(np.array([1.0, 2.0, 0.0, 4.0]))
    np.testing.assert_allclose(values[[0, 1, 3]], [0.0, math.log(2.0), math.log(4.0)])
    assert np.isnan(values[2])
    np.testing.assert_array_equal(valid, [True, True, False, True])


def test_lifted_angle_is_smooth_across_positive_to_negative_branch_cut() -> None:
    physical = np.deg2rad(np.array([170.0, 179.0, -179.0, -170.0]))
    lifted = experiment.lifted_angle_history(physical)

    np.testing.assert_allclose(lifted, np.deg2rad([170.0, 179.0, 181.0, 190.0]))
    assert np.all(np.diff(lifted) > 0.0)


def test_lifted_angle_is_smooth_across_negative_to_positive_branch_cut() -> None:
    physical = np.deg2rad(np.array([-170.0, -179.0, 179.0, 170.0]))
    lifted = experiment.lifted_angle_history(physical)

    np.testing.assert_allclose(lifted, np.deg2rad([-170.0, -179.0, -181.0, -190.0]))
    assert np.all(np.diff(lifted) < 0.0)


def test_lifted_angle_preserves_multiple_signed_revolutions() -> None:
    continuous = 0.2 + np.linspace(0.0, 10.0 * math.pi, 101)
    physical = experiment.wrap_angle_difference(continuous)
    lifted = experiment.lifted_angle_history(physical)
    revolutions = experiment.revolution_history(lifted)

    np.testing.assert_allclose(lifted, continuous, atol=2.0e-14)
    assert math.isclose(revolutions[-1], 5.0, abs_tol=2.0e-14)


def test_lifted_angle_preserves_reversed_rotational_direction() -> None:
    continuous = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 3.0, 2.0, 1.0, 0.0, -1.0, -2.0])
    physical = experiment.wrap_angle_difference(continuous)
    lifted = experiment.lifted_angle_history(physical)
    revolutions = experiment.revolution_history(lifted)

    np.testing.assert_allclose(lifted, continuous)
    assert revolutions[4] > revolutions[5]
    assert revolutions[-1] < 0.0


def test_same_physical_angle_can_have_different_winding_history() -> None:
    time = np.linspace(0.0, 1.6, 17)
    reference_physical = np.zeros_like(time)
    nearby_continuous = np.linspace(0.0, 2.0 * math.pi, len(time))
    nearby_physical = experiment.wrap_angle_difference(nearby_continuous)

    reference_lifted = experiment.lifted_angle_history(reference_physical)
    nearby_lifted = experiment.lifted_angle_history(nearby_physical)
    delta_revolutions = (
        experiment.revolution_history(nearby_lifted)
        - experiment.revolution_history(reference_lifted)
    )

    assert math.isclose(
        experiment.wrap_angle_difference(nearby_physical[-1] - reference_physical[-1]),
        0.0,
        abs_tol=1.0e-14,
    )
    assert math.isclose(delta_revolutions[-1], 1.0, abs_tol=1.0e-14)
    assert experiment.first_absolute_revolution_difference_time(time, delta_revolutions) == 1.6
