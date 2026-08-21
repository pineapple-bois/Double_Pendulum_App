"""Experiment-local tests for direction-preserving EL renormalisation."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

EXPERIMENT_ROOT = Path(__file__).resolve().parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

import renormalised_local_stretching as experiment


def test_scaled_vector_normalization_uses_characteristic_time() -> None:
    physical = np.array([3.0e-6, -4.0e-6, 5.0e-6, -6.0e-6])
    target = 1.0e-5
    scaled, magnitude, direction, reset_physical = experiment.normalized_reset(
        physical, target
    )

    expected = np.array(
        [
            physical[0],
            physical[1],
            experiment.characteristic_time() * physical[2],
            experiment.characteristic_time() * physical[3],
        ]
    )
    np.testing.assert_allclose(scaled, expected)
    assert math.isclose(magnitude, np.linalg.norm(expected))
    assert math.isclose(np.linalg.norm(direction), 1.0)
    assert math.isclose(
        experiment.candidate_a_distance(reset_physical), target, rel_tol=0.0, abs_tol=1.0e-15
    )


def test_physical_state_reconstruction_recovers_exact_reset_magnitude() -> None:
    reference = np.array([0.2, -0.3, 1.1, -0.7])
    direction = np.array([0.2, -0.4, 0.8, math.sqrt(0.16)])
    direction /= np.linalg.norm(direction)
    target = 1.0e-5

    shadow = experiment.reconstruct_shadow_state(reference, direction, target)
    difference = experiment.wrapped_el_difference(reference, shadow)
    achieved = experiment.scaled_el_vector(difference)

    assert math.isclose(np.linalg.norm(achieved), target, rel_tol=0.0, abs_tol=1.0e-15)
    np.testing.assert_allclose(achieved / np.linalg.norm(achieved), direction, atol=1.0e-11)


def test_reset_is_equivariant_across_angular_branch_representatives() -> None:
    reference_positive = np.array([math.pi - 2.0e-6, -math.pi + 3.0e-6, 0.4, -0.2])
    reference_shifted = np.array(
        [reference_positive[0] - 2.0 * math.pi, reference_positive[1] + 2.0 * math.pi, 0.4, -0.2]
    )
    direction = np.array([0.8, -0.4, 0.3, -0.2])
    direction /= np.linalg.norm(direction)
    target = 1.0e-5

    positive_shadow = experiment.reconstruct_shadow_state(reference_positive, direction, target)
    shifted_shadow = experiment.reconstruct_shadow_state(reference_shifted, direction, target)

    positive_difference = experiment.wrapped_el_difference(reference_positive, positive_shadow)
    shifted_difference = experiment.wrapped_el_difference(reference_shifted, shifted_shadow)
    np.testing.assert_allclose(positive_difference, shifted_difference, atol=1.0e-15)
    np.testing.assert_allclose(
        experiment.scaled_el_vector(positive_difference) / target,
        direction,
        atol=1.0e-11,
    )


def test_normalized_reset_preserves_evolved_direction_not_initial_direction() -> None:
    evolved = np.array([2.0e-5, -1.0e-5, 7.0e-5, -3.0e-5])
    _, _, direction, reset_physical = experiment.normalized_reset(evolved, 1.0e-5)
    achieved_direction = experiment.scaled_el_vector(reset_physical)
    achieved_direction /= np.linalg.norm(achieved_direction)

    np.testing.assert_allclose(achieved_direction, direction)
    assert np.count_nonzero(np.abs(direction) > 0.0) == 4
    assert not np.allclose(direction, [0.0, 1.0, 0.0, 0.0])


def test_contraction_cycle_retains_negative_log_stretching() -> None:
    growth, log_growth = experiment.growth_contribution(4.0e-6, 1.0e-5)

    assert math.isclose(growth, 0.4)
    assert log_growth < 0.0
    assert math.isclose(log_growth, math.log(0.4))


def test_cumulative_logarithmic_sum_and_rate_include_contractions() -> None:
    logs = np.array([math.log(2.0), math.log(0.5), math.log(3.0)])
    times = np.array([0.25, 0.5, 0.75])
    cumulative, rates = experiment.cumulative_rates(logs, times)

    np.testing.assert_allclose(cumulative, [math.log(2.0), 0.0, math.log(3.0)])
    np.testing.assert_allclose(rates, cumulative / times)


def test_deterministic_cycle_timing_uses_integer_cycle_indices() -> None:
    times = experiment.deterministic_cycle_times(1.0, 0.125)

    np.testing.assert_array_equal(times, np.linspace(0.0, 1.0, 9))
    with pytest.raises(ValueError):
        experiment.deterministic_cycle_times(1.0, 0.3)


def test_invalid_cycle_is_explicitly_rejected() -> None:
    checks = experiment.cycle_validity(
        solver_accepted=False,
        pre_reset_a=0.0,
        pre_reset_b=1.0e-5,
        achieved_reset_a=1.0e-5,
        target_reset_a=1.0e-5,
        direction_error=0.0,
        reconstruction_error=0.0,
        segment_energy_drift=0.0,
        finite_accumulation=False,
    )

    assert not all(checks.values())
    assert checks["solver_and_state_valid"] is False
    assert checks["candidate_a_pre_reset_positive_finite"] is False
    assert checks["accumulation_finite"] is False


def test_local_ceiling_failure_is_not_silently_accepted() -> None:
    checks = experiment.cycle_validity(
        solver_accepted=True,
        pre_reset_a=experiment.LOCAL_DISTANCE_CEILING * 1.01,
        pre_reset_b=1.0e-5,
        achieved_reset_a=1.0e-5,
        target_reset_a=1.0e-5,
        direction_error=0.0,
        reconstruction_error=0.0,
        segment_energy_drift=0.0,
        finite_accumulation=True,
    )

    assert checks["inside_empirical_local_ceiling"] is False
    assert not all(checks.values())


def test_zero_or_nonfinite_perturbations_cannot_be_renormalised() -> None:
    with pytest.raises(ValueError):
        experiment.normalized_reset(np.zeros(4), 1.0e-5)
    with pytest.raises(ValueError):
        experiment.growth_contribution(math.nan, 1.0e-5)
