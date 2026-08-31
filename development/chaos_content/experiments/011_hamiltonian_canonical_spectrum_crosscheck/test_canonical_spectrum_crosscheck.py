"""Focused regression checks for Experiment 011 Phases A--C."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

EXPERIMENT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

import canonical_spectrum_crosscheck as experiment


@pytest.fixture(scope="module")
def phase_a_result() -> dict[str, object]:
    return experiment.run_phase_a()


@pytest.fixture(scope="module")
def phase_b_result() -> dict[str, object]:
    return experiment.run_phase_b()


def synthetic_phase_c_run(spectrum: np.ndarray) -> dict[str, object]:
    cycles = []
    for cycle_index in range(1, 2561):
        time_value = cycle_index * experiment.PHASE_C_QR_INTERVAL_SECONDS
        cycles.append(
            {
                "end_time_seconds": time_value,
                "cumulative_finite_time_diagnostic_per_second": np.asarray(
                    spectrum, dtype=float
                ),
            }
        )
    return {
        "cycles": cycles,
        "_diagnostic": np.asarray(
            [cycle["cumulative_finite_time_diagnostic_per_second"] for cycle in cycles]
        ),
    }


def test_scaffold_history_and_source_inventory_remain_explicit() -> None:
    manifest = experiment.scaffold_manifest()

    assert manifest["status"] == "scaffold_history_preserved"
    assert manifest["scientific_result_available"] is False
    assert manifest["canonical_state_order"] == [
        "theta1",
        "theta2",
        "p_theta_1",
        "p_theta_2",
    ]
    assert manifest["experiment_010_target"]["mean_per_second"] == (
        0.983276,
        0.012274,
        -0.009941,
        -0.986532,
    )
    assert experiment.missing_source_paths(REPOSITORY_ROOT) == ()


def test_state_map_energy_and_periodicity_contract() -> None:
    dynamics = experiment.CanonicalDynamics()
    state = np.array([0.3, -0.7, 1.2, -0.8])
    canonical = experiment.el_to_canonical(state)

    assert np.allclose(experiment.canonical_to_el(canonical), state, rtol=0.0, atol=1.0e-12)
    assert np.allclose(
        experiment.inverse_tangent_map(canonical)
        @ experiment.forward_tangent_map(state),
        np.eye(4),
        rtol=0.0,
        atol=1.0e-12,
    )
    shifted = canonical + np.array([4.0 * math.pi, -2.0 * math.pi, 0.0, 0.0])
    assert dynamics.energy(shifted) == pytest.approx(dynamics.energy(canonical), abs=1.0e-9)
    assert np.allclose(dynamics.flow(shifted), dynamics.flow(canonical), rtol=0.0, atol=1.0e-9)
    assert np.allclose(dynamics.jacobian(shifted), dynamics.jacobian(canonical), rtol=0.0, atol=1.0e-9)


def test_phase_a_accepts_every_predeclared_group(phase_a_result: dict[str, object]) -> None:
    experiment.assert_self_check(phase_a_result)
    assert phase_a_result["accepted"] is True
    assert all(group["accepted"] for group in phase_a_result["groups"].values())


def test_phase_a_jacobian_and_reference_evidence(phase_a_result: dict[str, object]) -> None:
    groups = phase_a_result["groups"]
    jacobian = groups["jacobian_validation"]
    references = groups["reference_flow_validation"]
    tangent = groups["tangent_validation"]

    assert jacobian["tested_state_count"] == 7
    assert jacobian["maximum_assessment_relative_error"] <= experiment.LIMITS["jacobian_directional_relative"]
    assert jacobian["maximum_hamiltonian_matrix_residual"] <= experiment.LIMITS["hamiltonian_matrix_residual"]
    assert references["runs"]["refined"]["maximum_el_canonical_candidate_a_distance"] <= experiment.LIMITS["refined_reference_candidate_a"]
    assert tangent["maximum_relative_candidate_a_norm_error"] <= experiment.LIMITS["tangent_relative_norm"]
    assert tangent["minimum_signed_direction_cosine"] >= 1.0 - experiment.LIMITS["tangent_direction_cosine_shortfall"]


def test_metric_factor_reconstructs_and_phase_c_interface_is_explicit(
    phase_a_result: dict[str, object],
) -> None:
    metric = phase_a_result["groups"]["metric_analysis"]
    assert metric["accepted"] is True
    assert metric["maximum_inverse_reconstruction_error"] <= experiment.LIMITS["metric_reconstruction_absolute"]
    assert experiment.run_crosscheck is not None
    assert experiment.PHASE_C_DURATION_SECONDS == 640.0
    assert experiment.PHASE_C_QR_INTERVAL_SECONDS == 0.25


def test_phase_b_initial_bases_share_candidate_a_identity() -> None:
    canonical_state = experiment.el_to_canonical(experiment.INITIAL_EL_STATE)
    factor = experiment.candidate_a_pullback_factor(canonical_state)
    canonical_basis = np.linalg.solve(factor, np.eye(4))
    coordinate_map = experiment.inverse_tangent_map(canonical_state)
    el_basis = experiment.experiment007.initial_physical_tangent_basis()

    np.testing.assert_allclose(factor @ canonical_basis, np.eye(4), atol=1.0e-14)
    np.testing.assert_allclose(
        coordinate_map @ canonical_basis, el_basis, atol=1.0e-14
    )


def test_state_dependent_pullback_reset_reconstructs_in_both_coordinates() -> None:
    canonical_state = experiment.el_to_canonical(np.array([0.3, -0.7, 1.2, -0.8]))
    tangent_pre = np.array(
        [
            [1.2, 0.1, -0.2, 0.3],
            [-0.4, 1.4, 0.5, -0.1],
            [0.2, -0.3, 2.1, 0.4],
            [0.1, 0.6, -0.5, 1.8],
        ]
    )
    reset = experiment.canonical_pullback_qr_reset(canonical_state, tangent_pre)
    initial_factor = experiment.candidate_a_pullback_factor(
        experiment.el_to_canonical(experiment.INITIAL_EL_STATE)
    )

    assert reset["accepted"]
    assert not np.allclose(reset["factor"], initial_factor, rtol=0.0, atol=1.0e-8)
    assert np.all(np.diag(reset["upper"]) > 0.0)
    np.testing.assert_allclose(
        reset["factor"] @ tangent_pre,
        reset["orthogonal"] @ reset["upper"],
        atol=experiment.PHASE_B_QR_LIMIT,
    )
    np.testing.assert_allclose(
        tangent_pre,
        reset["tangent_matrix_post"] @ reset["upper"],
        atol=experiment.PHASE_B_QR_LIMIT,
    )
    np.testing.assert_allclose(
        reset["mapped_physical_pre"],
        reset["mapped_physical_post"] @ reset["upper"],
        atol=experiment.PHASE_B_QR_LIMIT,
    )


def test_canonical_full_matrix_rhs_applies_jacobian_to_each_column() -> None:
    dynamics = experiment.CanonicalDynamics()
    reference = experiment.el_to_canonical(np.array([0.3, -0.7, 1.2, -0.8]))
    tangent = np.arange(1.0, 17.0).reshape(4, 4) / 10.0
    augmented = experiment.experiment007.pack_augmented_state(reference, tangent)
    actual = experiment.canonical_full_matrix_augmented_rhs(dynamics, 0.4, augmented)
    actual_reference, actual_tangent = experiment.experiment007.unpack_augmented_state(actual)

    np.testing.assert_allclose(actual_reference, dynamics.flow(reference, 0.4))
    np.testing.assert_allclose(
        actual_tangent, dynamics.jacobian(reference, 0.4) @ tangent
    )


def test_phase_b_accepts_internal_cross_and_refinement_groups(
    phase_b_result: dict[str, object],
) -> None:
    experiment.assert_self_check(phase_b_result)
    assert phase_b_result["accepted"] is True
    assert phase_b_result["cycle_count"] == experiment.PHASE_B_CYCLE_COUNT
    assert all(group["accepted"] for group in phase_b_result["groups"].values())


def test_phase_b_bookkeeping_and_cross_formulation_limits(
    phase_b_result: dict[str, object],
) -> None:
    for run in phase_b_result["canonical_runs"].values():
        assert run["cumulative_bookkeeping_error"] <= experiment.PHASE_B_BOOKKEEPING_LIMIT
        assert run["diagnostic_bookkeeping_error"] <= experiment.PHASE_B_BOOKKEEPING_LIMIT
        assert run["maximum_post_pullback_orthonormality_error"] <= experiment.PHASE_B_QR_LIMIT
        assert run["maximum_physical_reconstruction_relative_error"] <= experiment.PHASE_B_QR_LIMIT
        cycle_logs = np.asarray(
            [cycle["cycle_log_growth"] for cycle in run["cycles"]], dtype=float
        )
        np.testing.assert_allclose(
            np.cumsum(cycle_logs, axis=0),
            run["_cumulative_logs"],
            rtol=0.0,
            atol=experiment.PHASE_B_BOOKKEEPING_LIMIT,
        )

    for comparison in phase_b_result["cross_formulation"].values():
        assert comparison["maximum_cycle_log_absolute_difference"] <= experiment.PHASE_B_CROSS_LIMITS["cycle_log_absolute"]
        assert comparison["maximum_cumulative_log_absolute_difference"] <= experiment.PHASE_B_CROSS_LIMITS["cumulative_log_absolute"]
        assert comparison["maximum_final_diagnostic_difference_per_second"] <= experiment.PHASE_B_CROSS_LIMITS["final_diagnostic_per_second"]


def test_phase_c_protocol_inherits_experiment_010_limits_and_policies() -> None:
    specs = experiment.phase_c_shadow_specs()

    assert tuple(specs) == ("baseline", "strict", "half_step")
    assert specs["baseline"][1] == experiment.BASELINE_MAX_STEP
    assert specs["strict"][1] == experiment.BASELINE_MAX_STEP
    assert specs["half_step"][1] == experiment.REFINED_MAX_STEP
    assert experiment.PHASE_C_MAX_CHANGE_480_TO_560 == 0.08
    assert experiment.PHASE_C_MAX_CHANGE_560_TO_640 == 0.05
    assert experiment.PHASE_C_MAX_WITHIN_LATE_RANGE == 0.05
    assert experiment.PHASE_C_MAX_FINAL_BETWEEN_RANGE == 0.05
    assert experiment.PHASE_C_MAX_FINAL_BETWEEN_SAMPLE_STD == 0.025
    assert experiment.PHASE_C_MAX_ENSEMBLE_MEAN_CHANGE_560_TO_640 == 0.04
    assert experiment.PHASE_C_MAX_LATE_WINDOW_BETWEEN_RANGE == 0.07


def test_phase_c_el_evidence_reproduces_committed_target() -> None:
    evidence = experiment.phase_c_el_evidence()

    np.testing.assert_allclose(
        evidence["ensemble_mean_640_per_second"],
        experiment.EXPERIMENT_010_TARGET.mean_per_second,
        rtol=0.0,
        atol=5.0e-7,
    )
    np.testing.assert_allclose(
        evidence["descriptive_uncertainty_half_width_per_second"],
        experiment.EXPERIMENT_010_TARGET.descriptive_half_width_per_second,
        rtol=0.0,
        atol=5.0e-7,
    )


def test_phase_c_internal_statistics_accept_settled_synthetic_ensemble() -> None:
    el = experiment.phase_c_el_evidence()["shadow_values_640_per_second"]
    runs = {
        name: synthetic_phase_c_run(value)
        for name, value in zip(("baseline", "strict", "half_step"), el)
    }
    within = {
        name: experiment.phase_c_within_shadow_analysis(run)
        for name, run in runs.items()
    }
    between = experiment.phase_c_between_shadow_analysis(runs)

    assert all(item["accepted"] for item in within.values())
    assert between["accepted"] is True
    assert experiment.phase_c_internal_verdict(
        numerical_validity_accepted=True,
        decorrelation_accepted=True,
        within=within,
        between=between,
    ) == "accepted_canonical_internal_compatibility_at_640_seconds"


def test_phase_c_cross_rule_accepts_overlap_and_rejects_material_shift() -> None:
    el = experiment.phase_c_el_evidence()["shadow_values_640_per_second"]
    names = ("baseline", "strict", "half_step")
    compatible_runs = {
        name: synthetic_phase_c_run(value) for name, value in zip(names, el)
    }
    compatible_between = experiment.phase_c_between_shadow_analysis(compatible_runs)
    compatible = experiment.phase_c_cross_formulation_analysis(
        canonical_runs=compatible_runs,
        canonical_between=compatible_between,
        canonical_internal_accepted=True,
    )
    assert compatible["accepted"] is True

    shift = np.array([0.08, 0.0, 0.0, -0.08])
    incompatible_runs = {
        name: synthetic_phase_c_run(value + shift) for name, value in zip(names, el)
    }
    incompatible_between = experiment.phase_c_between_shadow_analysis(
        incompatible_runs
    )
    incompatible = experiment.phase_c_cross_formulation_analysis(
        canonical_runs=incompatible_runs,
        canonical_between=incompatible_between,
        canonical_internal_accepted=True,
    )
    assert incompatible["accepted"] is False
    assert incompatible["verdict"] == (
        "rejected_descriptive_cross_formulation_compatibility"
    )
    assert incompatible["checks"][
        "terminal_mean_displacement_within_0.05_per_second"
    ] is False
