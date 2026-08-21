"""Experiment-local tests for direction-preserving EL renormalisation."""

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

import renormalised_local_stretching as experiment


@pytest.fixture(scope="module")
def dynamics():
    return experiment.build_dynamics()


def test_el_rhs_is_invariant_under_independent_integer_turn_shifts(dynamics) -> None:
    state = np.array([0.73, -1.21, 2.4, -3.1])
    expected = np.asarray(dynamics._system(state, 0.37), dtype=float)
    for turns in ((1, -1), (-7, 4), (23, -19)):
        shifted = np.array(state, copy=True)
        shifted[:2] += 2.0 * math.pi * np.asarray(turns)
        actual = np.asarray(dynamics._system(shifted, 0.37), dtype=float)
        np.testing.assert_allclose(actual, expected, rtol=1.0e-12, atol=1.0e-11)


def test_physical_observables_are_invariant_under_equivalent_angles() -> None:
    state = np.array([0.73, -1.21, 2.4, -3.1])
    shifted = np.array(state, copy=True)
    shifted[:2] += 2.0 * math.pi * np.array([-11, 8])

    np.testing.assert_allclose(
        experiment.cartesian_full_state(shifted),
        experiment.cartesian_full_state(state),
        rtol=1.0e-12,
        atol=1.0e-12,
    )
    np.testing.assert_allclose(
        experiment.simple_energy(shifted),
        experiment.simple_energy(state),
        rtol=1.0e-12,
        atol=1.0e-12,
    )


def test_local_angular_rebasing_and_branch_crossing() -> None:
    state = np.array(
        [math.pi + 2.0e-6, -math.pi - 3.0e-6, 0.4, -0.2]
    )
    canonical = experiment.canonicalize_state_angles(state)

    assert -math.pi < canonical[0] <= math.pi
    assert -math.pi < canonical[1] <= math.pi
    np.testing.assert_allclose(
        experiment.wrap_angle_difference(canonical[:2] - state[:2]), [0.0, 0.0]
    )
    np.testing.assert_array_equal(canonical[2:], state[2:])


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


@pytest.mark.parametrize("target", [1.0e-5, 1.0e-6])
def test_reset_is_conditioned_at_large_synthetic_winding_count(target: float) -> None:
    reference = np.array(
        [2.0 * math.pi * 1_000_000 + 0.2, -2.0 * math.pi * 800_000 - 0.3, 1.1, -0.7]
    )
    direction = np.array([0.2, -0.4, 0.8, math.sqrt(0.16)])
    direction /= np.linalg.norm(direction)

    shadow = experiment.reconstruct_shadow_state(reference, direction, target)
    local_reference = experiment.canonicalize_state_angles(reference)
    achieved = experiment.scaled_el_vector(
        experiment.wrapped_el_difference(local_reference, shadow)
    )
    achieved_norm = np.linalg.norm(achieved)

    assert abs(achieved_norm - target) / target <= experiment.RESET_RELATIVE_TOLERANCE
    np.testing.assert_allclose(
        achieved / achieved_norm,
        direction,
        rtol=0.0,
        atol=experiment.DIRECTION_ABSOLUTE_TOLERANCE,
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


def test_winding_bookkeeping_handles_turns_reversals_and_branches() -> None:
    positive = np.linspace(0.2, 4.0 * math.pi + 0.2, 33)
    reverse = np.linspace(4.0 * math.pi + 0.2, -2.0 * math.pi + 0.2, 49)[1:]
    physical = np.concatenate((positive, reverse))
    second = -0.5 * physical
    lifted_expected = np.column_stack((physical, second))
    local = experiment.wrap_angle_difference(lifted_expected)

    reconstructed = experiment.accumulate_lifted_angles(local)

    np.testing.assert_allclose(reconstructed, lifted_expected, atol=2.0e-14)
    np.testing.assert_allclose(
        experiment.wrap_angle_difference(reconstructed), local, atol=2.0e-14
    )
    assert np.max(reconstructed[:, 0]) > 2.0 * math.pi
    assert reconstructed[-1, 0] < reconstructed[-10, 0]


def test_explicit_max_step_is_forwarded_to_solve_ivp(monkeypatch) -> None:
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
    result = experiment.solve_segment(
        SimpleNamespace(_system=lambda state, time: state),
        initial,
        requested,
        experiment.SIMPLE_REFERENCE_SOLVER_POLICY,
        max_step=0.0125,
    )

    assert result["accepted"]
    assert captured["max_step"] == 0.0125
    assert result["solver_status"]["max_step_seconds"] == 0.0125


def test_segment_energy_is_measured_from_post_reset_segment_start() -> None:
    post_reset = np.array([0.7, -0.4, 1.2, -0.8])
    later = np.array([0.71, -0.39, 1.19, -0.79])
    state = np.vstack((post_reset, later))

    drift = experiment.normalized_segment_energy_drift(state)
    expected = abs(
        experiment.simple_energy(later)[0] - experiment.simple_energy(post_reset)[0]
    ) / experiment.energy_scale()

    assert drift[0] == 0.0
    assert math.isclose(drift[1], expected, rel_tol=0.0, abs_tol=1.0e-16)


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
