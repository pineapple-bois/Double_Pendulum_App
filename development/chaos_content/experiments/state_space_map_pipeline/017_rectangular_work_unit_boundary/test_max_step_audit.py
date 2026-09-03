"""Focused regression tests for Experiment 017's max-step audit."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


EXPERIMENT_ROOT = Path(__file__).resolve().parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

import max_step_audit as audit


@pytest.fixture(scope="module")
def assessment() -> dict[str, object]:
    return audit.run_audit()


def test_selected_cases_are_existing_failures_and_immediate_neighbors() -> None:
    assert tuple(
        (
            case.name,
            case.source_grid,
            case.theta1_index,
            case.theta2_index,
            case.expected_promoted_status,
        )
        for case in audit.AUDIT_CASES
    ) == (
        ("17x17_failure", "17x17", 7, 1, "execution_error"),
        ("17x17_left_neighbor", "17x17", 6, 1, "completed_valid"),
        ("25x25_failure", "25x25", 15, 2, "execution_error"),
        ("25x25_left_neighbor", "25x25", 14, 2, "completed_valid"),
    )


def test_failing_cells_have_real_fortran_endpoint_step_violations(
    assessment: dict[str, object],
) -> None:
    failing = [
        case
        for case in assessment["cases"]
        if case["promoted_evaluation"]["status"] == "execution_error"
    ]
    assert len(failing) == 2
    for case in failing:
        assert case["fortran_unchecked"]["violating_segment_numbers"] == [9]
        trace = case["fortran_unchecked"]["segments"][8]
        assert trace["start_time"] == 2.0
        assert trace["end_time"] == 2.25
        assert trace["configured_fortran_max_step"] == (
            trace["requested_max_step"]
        )
        assert trace["maximum_step_gap"] > trace["requested_max_step"]
        assert trace["maximum_step_gap"] <= 1.01 * trace["requested_max_step"]
        assert trace["maximum_gap_is_endpoint_step"]
        assert trace["endpoint_reached"]
        assert trace["successful"]
        assert trace["return_code"] == 1
        assert trace["all_states_finite"]
        assert trace["accepted_step_count"] == (
            trace["reported_fortran_accepted_step_count"]
        )
        replay = case["no_solout_replays"][0]
        assert replay["successful"]
        assert replay[
            "maximum_final_state_absolute_difference_from_solout_run"
        ] == 0.0


def test_neighboring_cells_and_solve_ivp_oracles_respect_the_cap(
    assessment: dict[str, object],
) -> None:
    neighbors = [
        case
        for case in assessment["cases"]
        if case["promoted_evaluation"]["status"] == "completed_valid"
    ]
    assert len(neighbors) == 2
    assert all(
        not case["fortran_unchecked"]["violating_segment_numbers"]
        for case in neighbors
    )
    for case in assessment["cases"]:
        traced = case["compiled_solve_ivp_oracle"]["traced_internal_steps"]
        assert not traced["violating_segment_numbers"]
        assert traced["comparison_to_uniform_grid_oracle"]["accepted"]
        assert case["mathematical_solve_ivp_oracle"][
            "comparison_to_compiled_solve_ivp_oracle"
        ]["accepted"]


def test_conservative_internal_cap_is_only_a_supported_repair_probe(
    assessment: dict[str, object],
) -> None:
    for case in assessment["cases"]:
        probe = case["conservative_fortran_probe"]
        assert probe["diagnostic_only"]
        assert not probe["violating_segment_numbers"]
        assert probe["comparison_to_compiled_solve_ivp_oracle"]["accepted"]
        assert probe["maximum_accepted_step_gap"] <= (
            case["resolved_contract"]["requested_max_step_seconds"]
        )
    assert not assessment["repair"]["promoted_wrapper_change_justified"]


def test_audit_concludes_current_errors_are_authoritative(
    assessment: dict[str, object],
) -> None:
    assert assessment["decision"] == "A"
    assert assessment["aggregate_checks"]["all_case_checks_passed"]
    assert assessment["aggregate_checks"][
        "all_failing_violations_are_endpoint_steps"
    ]
    assert assessment["aggregate_checks"][
        "callback_counts_match_fortran_accepted_counts"
    ]
    assert assessment["aggregate_checks"][
        "no_solout_final_states_match_observed_runs_exactly"
    ]
    assert assessment["aggregate_checks"][
        "all_solve_ivp_internal_steps_respect_max_step"
    ]
