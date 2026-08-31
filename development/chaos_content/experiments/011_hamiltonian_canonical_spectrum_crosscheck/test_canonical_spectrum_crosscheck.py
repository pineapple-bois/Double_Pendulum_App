"""Focused regression checks for Experiment 011 Phase A."""

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


def test_metric_factor_reconstructs_and_future_qr_is_unavailable(
    phase_a_result: dict[str, object],
) -> None:
    metric = phase_a_result["groups"]["metric_analysis"]
    assert metric["accepted"] is True
    assert metric["maximum_inverse_reconstruction_error"] <= experiment.LIMITS["metric_reconstruction_absolute"]
    with pytest.raises(NotImplementedError, match="does not implement canonical QR"):
        experiment.run_crosscheck()
