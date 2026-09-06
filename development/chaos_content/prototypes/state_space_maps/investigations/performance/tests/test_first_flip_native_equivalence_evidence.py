"""Regression checks for the bounded native-equivalence diagnosis."""

from __future__ import annotations

import json
from pathlib import Path


EVIDENCE = Path(__file__).resolve().parents[1] / "evidence/current/first_flip_native_dop853_equivalence.json"


def test_equivalence_diagnosis_reproduces_both_bounded_defects() -> None:
    payload = json.loads(EVIDENCE.read_text())
    summary = payload["summary"]
    assert summary["cell_count"] == 4096
    assert summary["max_step_recovery_count"] == 62
    assert summary["max_step_recovery_observed_count"] == 0
    assert summary["max_step_recovery_censored_count"] == 62
    assert summary["baseline_maximum_event_time_difference"] > 5.0e-8
    assert summary["strict_max_step_violation_count"] == 0
    assert summary["strict_maximum_event_time_difference"] > 5.0e-8


def test_narrow_rejection_and_horizon_corrections_clear_bounded_gates() -> None:
    summary = json.loads(EVIDENCE.read_text())["summary"]
    assert summary["rejection_fixed_max_step_violation_count"] == 0
    assert summary["rejection_fixed_classification_mismatch_count"] == 0
    assert summary["rejection_fixed_maximum_event_time_difference"] <= 5.0e-8
    assert summary["scipy_recovery_max_step_violation_count"] == 0


def test_native_failure_is_deterministic() -> None:
    repeats = json.loads(EVIDENCE.read_text())["determinism_repeats"]
    keys = ("maximum_step", "last_step_start", "last_step_end", "event_time")
    assert len({tuple(record[key] for key in keys) for record in repeats}) == 1
