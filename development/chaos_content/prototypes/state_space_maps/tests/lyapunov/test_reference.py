"""Focused contract tests for the Sensitivity-to-Lyapunov reference."""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pytest

STATE_SPACE_MAPS_ROOT = Path(__file__).resolve().parents[2]

from development.chaos_content.prototypes.state_space_maps.src.lyapunov.reference import (
    CandidateAMetric,
    EulerLagrangeDynamics,
    PendulumParameters,
    RenormalizedTangentSpec,
    SensitivitySpec,
    run_renormalized_tangent,
    run_sensitivity_to_lyapunov,
    second_bob_separation,
    wrap_angle_difference,
)
from development.chaos_content.prototypes.state_space_maps.runners.render_sensitivity_to_lyapunov import DEFAULT_FIGURE_PATH, build_figure
from src.double_pendulum.models import (
    SIMPLE_REFERENCE_SOLVER_POLICY,
    DoublePendulumLagrangian,
)


@pytest.fixture(scope="module")
def result():
    return run_sensitivity_to_lyapunov()


@pytest.fixture(scope="module")
def dynamics():
    return EulerLagrangeDynamics(PendulumParameters())


@pytest.fixture(scope="module")
def renormalized_result():
    return run_renormalized_tangent()


def test_wrapped_finite_angles_use_deterministic_positive_pi_branch() -> None:
    np.testing.assert_array_equal(
        wrap_angle_difference(np.array([-math.pi, math.pi, 3.0 * math.pi])),
        [math.pi, math.pi, math.pi],
    )
    metric = CandidateAMetric(characteristic_length=1.0, gravity=9.81)
    reference = np.array([math.pi - 1.0e-7, -math.pi + 2.0e-7, 0.4, -0.2])
    nearby = np.array([-math.pi + 3.0e-7, math.pi - 5.0e-7, 0.4, -0.2])
    difference = metric.finite_difference(reference, nearby)
    assert difference[0] > 0.0
    assert difference[1] < 0.0


def test_candidate_a_geometry_scales_only_velocity_components() -> None:
    metric = CandidateAMetric(characteristic_length=1.0, gravity=9.81)
    physical = np.array([1.0, -2.0, 3.0, -4.0])
    expected = np.array([1.0, -2.0, 3.0 / math.sqrt(9.81), -4.0 / math.sqrt(9.81)])
    np.testing.assert_allclose(metric.scale_tangent(physical), expected)
    np.testing.assert_allclose(metric.scaling_matrix() @ physical, expected)


def test_symbolic_flow_matches_accepted_production_rhs(dynamics) -> None:
    parameters = PendulumParameters()
    production = DoublePendulumLagrangian(
        parameters.symbolic_substitutions(),
        [179.0, 179.0, 0.0, 0.0],
        [0.0, 1.0e-6, 2],
        model="simple",
        solver_policy=SIMPLE_REFERENCE_SOLVER_POLICY,
    )
    for state, time_value in (
        (np.array([0.73, -1.21, 2.4, -3.1]), 0.37),
        (np.deg2rad([179.0, 179.0, 0.0, 0.0]), 0.0),
    ):
        np.testing.assert_allclose(
            dynamics.flow(time_value, state),
            np.asarray(production._system(state, time_value), dtype=float),
            rtol=0.0,
            atol=1.0e-13,
        )


def test_jacobian_matches_independent_directional_finite_difference(dynamics) -> None:
    state = np.array([0.73, -1.21, 2.4, -3.1])
    direction = np.array([0.3, -0.4, 0.5, -0.7])
    direction /= np.linalg.norm(direction)
    time_value = 0.37
    step = 1.0e-6
    expected = dynamics.jacobian(time_value, state) @ direction
    observed = (
        dynamics.flow(time_value, state + step * direction)
        - dynamics.flow(time_value, state)
    ) / step
    relative_error = np.linalg.norm(observed - expected) / np.linalg.norm(expected)
    assert relative_error <= 5.0e-5


def test_pair_geometry_and_candidate_a_initial_values(result) -> None:
    pair = result.finite_pair
    spec = result.spec
    assert pair.reference.state.shape == (130, 4)
    assert pair.nearby.state.shape == (130, 4)
    assert pair.reference.second_bob_xy.shape == (130, 2)
    assert pair.candidate_a_separation[0] == pytest.approx(1.0e-6, abs=2.0e-12)
    expected_bob = 2.0 * spec.parameters.length2 * math.sin(0.5e-6)
    assert pair.second_bob_separation[0] == pytest.approx(expected_bob, abs=2.0e-12)
    geometric_bound = 2.0 * (spec.parameters.length1 + spec.parameters.length2)
    assert np.all(pair.second_bob_separation <= geometric_bound + 2.0e-12)
    np.testing.assert_allclose(
        pair.second_bob_separation,
        second_bob_separation(
            pair.reference.state, pair.nearby.state, spec.parameters
        ),
    )


def test_direct_tangent_preserves_unwrapped_components_and_rate_identity(result) -> None:
    tangent = result.tangent
    assert tangent.candidate_a_norm[0] == pytest.approx(1.0, abs=1.0e-14)
    assert math.isnan(tangent.finite_time_rate[0])
    np.testing.assert_allclose(
        tangent.finite_time_rate[1:],
        tangent.log_stretch[1:] / tangent.time[1:],
        rtol=0.0,
        atol=0.0,
    )
    assert abs(tangent.vector[-1, 1]) > 2.0 * math.pi


def test_normalized_finite_shadow_reproduces_tangent_local_limit(result) -> None:
    finite_log = np.log(result.finite_pair.normalized_candidate_a_separation)
    maximum_log_error = float(np.max(np.abs(finite_log - result.tangent.log_stretch)))
    assert maximum_log_error <= 7.0e-5
    assert float(np.min(result.finite_to_tangent_direction_cosine)) >= 0.999
    assert np.all(result.finite_pair.local_comparison_mask)
    assert result.finite_pair.local_prefix_end_time == pytest.approx(1.29)


def test_trusted_experiment_006_endpoint_regression(result) -> None:
    # Selected baseline fixtures from the accepted Experiment 006 output.
    np.testing.assert_allclose(
        result.finite_pair.reference.state[-1],
        [
            2.02922289708029,
            -2.1241589207682536,
            -3.0898268868546586,
            2.203947663211029,
        ],
        rtol=0.0,
        atol=2.0e-11,
    )
    assert result.tangent.candidate_a_norm[-1] == pytest.approx(
        100.17784057503277, abs=2.0e-8
    )
    assert result.tangent.log_stretch[-1] == pytest.approx(
        4.606947012247286, abs=2.0e-10
    )
    assert result.tangent.finite_time_rate[-1] == pytest.approx(
        3.5712767536800665, abs=2.0e-10
    )


def test_bounded_numerical_contract_is_satisfied(result) -> None:
    diagnostics = result.diagnostics
    assert diagnostics.reference_segment_count == 6
    assert diagnostics.nearby_segment_count == 6
    assert diagnostics.max_step_seconds == pytest.approx(
        math.sqrt(1.0 / 9.81) / 32.0
    )
    assert diagnostics.reference_max_normalized_energy_drift <= 1.0e-7
    assert diagnostics.nearby_max_normalized_energy_drift <= 1.0e-7


def test_default_spec_declares_experiment_006_local_contract() -> None:
    spec = SensitivitySpec()
    assert spec.duration == 1.29
    assert spec.sampling_interval == 0.01
    assert spec.chart_rebase_interval == 0.25
    assert spec.local_distance_ceiling == 1.0e-2
    assert spec.finite_perturbation == (0.0, 1.0e-6, 0.0, 0.0)


def test_first_figure_exposes_the_pedagogical_progression(result) -> None:
    figure = build_figure(result)
    titles = [axis.get_title() for axis in figure.axes]
    assert "1. Physical Cartesian separation" in titles
    assert "2. Finite Candidate-A state separation" in titles
    assert "3. Local tangent stretching" in titles
    assert any("not an asymptotic exponent" in title for title in titles)
    plt.close(figure)


def test_default_figure_path_is_strand_local() -> None:
    assert DEFAULT_FIGURE_PATH == (
        STATE_SPACE_MAPS_ROOT
        / "outputs"
        / "lyapunov"
        / "sensitivity_to_lyapunov.png"
    )


def test_renormalized_tangent_reproduces_experiment_007_prefix(
    renormalized_result,
) -> None:
    # Trusted one-vector fixtures from Experiment 007 at 0.25, 0.50, and 5 s.
    np.testing.assert_allclose(
        renormalized_result.stretch_factor[:2],
        [3.616321760409443, 4.387214198041842],
        rtol=0.0,
        atol=2.0e-10,
    )
    np.testing.assert_allclose(
        renormalized_result.log_stretch_increment[:2],
        [1.2854574209853458, 1.4786944466228358],
        rtol=0.0,
        atol=2.0e-10,
    )
    assert renormalized_result.cumulative_log_stretch[-1] == pytest.approx(
        5.196897087890645, abs=2.0e-10
    )
    assert renormalized_result.finite_time_stretching_rate == pytest.approx(
        1.039379417578129, abs=2.0e-10
    )


def test_renormalized_bookkeeping_and_numerical_invariants(
    renormalized_result,
) -> None:
    result = renormalized_result
    diagnostics = result.diagnostics
    assert len(result.cycle_end_time) == diagnostics.segment_count == 20
    np.testing.assert_allclose(
        np.log(result.stretch_factor),
        result.log_stretch_increment,
        rtol=0.0,
        atol=2.0e-16,
    )
    replayed_cumulative = []
    cumulative = 0.0
    for increment in result.log_stretch_increment:
        cumulative += float(increment)
        replayed_cumulative.append(cumulative)
    np.testing.assert_array_equal(result.cumulative_log_stretch, replayed_cumulative)
    np.testing.assert_allclose(
        result.cumulative_finite_time_rate,
        result.cumulative_log_stretch / result.cycle_end_time,
        rtol=0.0,
        atol=0.0,
    )
    assert np.any(result.log_stretch_increment < 0.0)
    assert result.metric.tangent_norm(result.initial_unit_tangent) == pytest.approx(1.0)
    assert result.metric.tangent_norm(result.final_unit_tangent) == pytest.approx(1.0)
    assert diagnostics.maximum_normalized_reference_energy_drift <= 1.0e-7
    assert diagnostics.maximum_post_renormalization_norm_error <= 1.0e-12
    assert diagnostics.numerically_valid
    assert diagnostics.validity_issues == ()


def test_renormalized_and_direct_tangent_logs_agree_over_short_horizon() -> None:
    renormalized = run_renormalized_tangent(
        RenormalizedTangentSpec(duration=0.5)
    )
    direct = run_sensitivity_to_lyapunov(
        SensitivitySpec(
            finite_perturbation=(1.0e-6, 0.0, 0.0, 0.0),
            duration=0.5,
        )
    )
    assert renormalized.cumulative_log_stretch[-1] == pytest.approx(
        direct.tangent.log_stretch[-1], abs=2.0e-11
    )


def test_renormalized_spec_requires_complete_intervals() -> None:
    with pytest.raises(ValueError, match="integer number"):
        RenormalizedTangentSpec(duration=1.1)
