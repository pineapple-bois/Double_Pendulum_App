"""Lightweight contract checks for the Experiment 011 scaffold."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

EXPERIMENT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

import canonical_spectrum_crosscheck as experiment


def test_scaffold_records_state_orders_target_and_no_result() -> None:
    manifest = experiment.scaffold_manifest()

    assert manifest["status"] == "scaffolded_in_preparation"
    assert manifest["scientific_result_available"] is False
    assert manifest["canonical_state_order"] == [
        "theta1",
        "theta2",
        "p_theta_1",
        "p_theta_2",
    ]
    assert manifest["el_state_order"] == ["theta1", "theta2", "omega1", "omega2"]
    assert manifest["experiment_010_target"]["mean_per_second"] == (
        0.983276,
        0.012274,
        -0.009941,
        -0.986532,
    )


def test_inventory_paths_exist() -> None:
    assert experiment.missing_source_paths(REPOSITORY_ROOT) == ()


def test_evidence_sequence_stops_computation_until_validation() -> None:
    assert experiment.EVIDENCE_SEQUENCE[-1] == "long_time_spectrum_comparison"
    with pytest.raises(NotImplementedError, match="scaffolding only"):
        experiment.run_crosscheck()
