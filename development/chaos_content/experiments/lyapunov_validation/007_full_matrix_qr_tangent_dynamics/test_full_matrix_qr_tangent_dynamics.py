"""Focused tests for the Experiment 007 full-matrix QR primitive."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

EXPERIMENT_ROOT = Path(__file__).resolve().parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

import full_matrix_qr_tangent_dynamics as experiment


@pytest.fixture(scope="module")
def dynamics():
    return experiment.experiment006.VariationalDynamics()


def test_initial_physical_basis_is_candidate_a_orthonormal() -> None:
    scale = experiment.scaling_matrix()
    physical_basis = experiment.initial_physical_tangent_basis()
    scaled_basis = scale @ physical_basis

    np.testing.assert_allclose(scaled_basis, np.eye(4), rtol=0.0, atol=1.0e-15)
    np.testing.assert_allclose(
        scaled_basis.T @ scaled_basis, np.eye(4), rtol=0.0, atol=1.0e-15
    )


def test_augmented_pack_unpack_preserves_column_matrix_order() -> None:
    reference = np.array([0.3, -0.7, 1.1, -1.5])
    tangent = np.arange(16, dtype=float).reshape(4, 4)
    packed = experiment.pack_augmented_state(reference, tangent)
    unpacked_reference, unpacked_tangent = experiment.unpack_augmented_state(packed)

    np.testing.assert_array_equal(unpacked_reference, reference)
    np.testing.assert_array_equal(unpacked_tangent, tangent)


def test_full_matrix_rhs_uses_validated_jacobian_on_each_column(dynamics) -> None:
    reference = np.array([0.73, -1.21, 2.4, -3.1])
    tangent = np.array(
        [
            [1.0, 0.2, -0.1, 0.4],
            [0.3, 1.1, 0.5, -0.2],
            [-0.4, 0.6, 0.9, 0.1],
            [0.7, -0.3, 0.2, 1.2],
        ]
    )
    actual = experiment.full_matrix_augmented_rhs(
        dynamics, 0.37, experiment.pack_augmented_state(reference, tangent)
    )
    actual_reference, actual_tangent = experiment.unpack_augmented_state(actual)

    np.testing.assert_allclose(actual_reference, dynamics.flow(reference, 0.37))
    np.testing.assert_allclose(
        actual_tangent, dynamics.jacobian(reference, 0.37) @ tangent
    )


def test_positive_diagonal_qr_is_deterministic_and_reconstructs_input() -> None:
    matrix = np.array(
        [
            [-2.0, 0.5, 0.1, -0.3],
            [0.4, 1.7, -0.6, 0.2],
            [0.3, -0.2, -1.4, 0.8],
            [-0.1, 0.6, 0.5, 1.3],
        ]
    )
    first_q, first_r = experiment.positive_diagonal_qr(matrix)
    second_q, second_r = experiment.positive_diagonal_qr(matrix)

    assert np.all(np.diag(first_r) > 0.0)
    np.testing.assert_allclose(first_q.T @ first_q, np.eye(4), atol=1.0e-15)
    np.testing.assert_allclose(first_q @ first_r, matrix, atol=1.0e-15)
    np.testing.assert_array_equal(first_q, second_q)
    np.testing.assert_array_equal(first_r, second_r)


def test_qr_reset_is_consistent_in_scaled_and_physical_coordinates() -> None:
    physical_pre = np.array(
        [
            [1.2, 0.1, -0.2, 0.3],
            [-0.4, 1.4, 0.5, -0.1],
            [0.2, -0.3, 2.1, 0.4],
            [0.1, 0.6, -0.5, 1.8],
        ]
    )
    reset = experiment.qr_reset(physical_pre)
    scale = experiment.scaling_matrix()
    physical_post = reset["tangent_matrix_post"]

    assert reset["accepted"]
    np.testing.assert_allclose(
        scale @ physical_pre,
        reset["orthogonal"] @ reset["upper"],
        atol=experiment.QR_ERROR_LIMIT,
    )
    np.testing.assert_allclose(
        physical_pre,
        physical_post @ reset["upper"],
        atol=experiment.QR_ERROR_LIMIT,
    )
    np.testing.assert_allclose(
        (scale @ physical_post).T @ (scale @ physical_post),
        np.eye(4),
        atol=experiment.QR_ERROR_LIMIT,
    )


def test_cycle_times_are_integer_indexed_and_reject_partial_cycles() -> None:
    np.testing.assert_array_equal(
        experiment.deterministic_cycle_times(1.0), np.linspace(0.0, 1.0, 5)
    )
    np.testing.assert_array_equal(
        experiment.deterministic_cycle_times(0.5, 0.125),
        np.linspace(0.0, 0.5, 5),
    )
    with pytest.raises(ValueError):
        experiment.deterministic_cycle_times(1.1)


def test_short_qr_run_has_finite_recomputable_bookkeeping(dynamics) -> None:
    run = experiment.run_qr_primitive(
        dynamics, run_id="focused_test", duration=0.5
    )

    assert run["accepted"]
    assert run["cycle_count"] == 2
    cycle_logs = np.asarray([cycle["cycle_log_growth"] for cycle in run["cycles"]])
    cumulative = np.cumsum(cycle_logs, axis=0)
    end_times = np.asarray([cycle["end_time_seconds"] for cycle in run["cycles"]])
    np.testing.assert_allclose(cumulative, run["_cumulative_logs"], atol=1.0e-15)
    np.testing.assert_allclose(
        cumulative / end_times[:, None],
        run["_finite_time_spectrum"],
        atol=1.0e-15,
    )
    assert np.all(np.isfinite(run["_finite_time_spectrum"]))


def test_short_qr_interval_has_complete_nonuniform_diagnostic_sampling(dynamics) -> None:
    run = experiment.run_qr_primitive(
        dynamics,
        run_id="short_qr_sampling",
        duration=0.25,
        qr_interval=0.125,
    )

    assert run["accepted"]
    assert run["checks"]["global_output_complete"]
    assert run["cycle_count"] == 2
    assert len(run["_reference_time"]) == 25


def test_exact_repeat_comparison_detects_reproducibility(dynamics) -> None:
    primary = experiment.run_qr_primitive(
        dynamics, run_id="repeat_primary", duration=0.5
    )
    repeat = experiment.run_qr_primitive(
        dynamics, run_id="repeat_check", duration=0.5
    )
    comparison = experiment.compare_exact_repeats(primary, repeat)

    assert comparison["accepted"]
    assert comparison["maximum_cycle_log_difference"] == 0.0
    assert comparison["maximum_finite_time_spectrum_difference"] == 0.0
    assert comparison["final_reference_candidate_a_distance"] == 0.0


def test_duration_convergence_uses_cumulative_values_not_cycle_logs() -> None:
    constant_spectrum = np.array([0.8, 0.0, 0.0, -0.8])
    cycles = [
        {
            "end_time_seconds": 0.25 * index,
            "cycle_log_growth": [99.0, -99.0, 31.0, -31.0],
            "cumulative_finite_time_spectrum_per_second": constant_spectrum.tolist(),
        }
        for index in range(1, 321)
    ]
    analysis = experiment.duration_convergence_analysis({"cycles": cycles})

    assert analysis["accepted"]
    assert analysis["maximum_component_change_20_to_40_per_second"] == 0.0
    assert analysis["maximum_component_change_40_to_80_per_second"] == 0.0
    assert analysis["maximum_final_quarter_range_per_second"] == 0.0


def test_one_vector_check_matches_first_qr_column_for_short_run(dynamics) -> None:
    qr_run = experiment.run_qr_primitive(
        dynamics, run_id="one_vector_qr", duration=0.5
    )
    one_vector = experiment.run_one_vector_renormalisation(dynamics, duration=0.5)
    comparison = experiment.compare_one_vector_to_qr(qr_run, one_vector)

    assert one_vector["accepted"]
    assert comparison["accepted"]
    assert comparison["absolute_difference_per_second"] <= 1.0e-12
