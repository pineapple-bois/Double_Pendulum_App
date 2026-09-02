"""Focused tests for the verified endpoint max-step fallback experiment."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


EXPERIMENT_ROOT = Path(__file__).resolve().parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

import max_step_fallback_boundary as experiment


@pytest.fixture(scope="module")
def known_cases() -> list[dict[str, object]]:
    return experiment.assess_known_cases()


def test_known_failures_fallback_and_neighbors_stay_fast(known_cases) -> None:
    assert [item["route"] for item in known_cases] == [
        experiment.FALLBACK_ROUTE,
        experiment.FAST_ROUTE,
        experiment.FALLBACK_ROUTE,
        experiment.FAST_ROUTE,
    ]
    for item in known_cases:
        assert item["status"] == "completed_valid"
        if item["historical_failure"]:
            assert item["fallback_exactly_equals_oracle"]
            assert item["verification"]["verified"]
            assert item["verification"]["violating_segments"] == (9,)
        else:
            assert item["evaluation_unchanged_from_fast"]
            assert item["verification"] is None


def test_five_experiment_015_fixtures_remain_on_fast_path() -> None:
    fixtures = experiment.assess_five_fixtures()

    assert len(fixtures) == 5
    assert all(item["route"] == experiment.FAST_ROUTE for item in fixtures)
    assert all(item["evaluation_unchanged"] for item in fixtures)
    assert all(item["comparison_to_oracle"]["accepted"] for item in fixtures)


def test_unrelated_failures_and_programming_errors_do_not_fallback() -> None:
    assessment = experiment.assess_failure_confinement()

    assert assessment["unrelated_errors_preserved"]
    assert assessment[
        "ordinary_nonfinite_endpoint_and_return_code_prefilter_rejected"
    ]
    assert assessment["lookalike_max_step_prefilter_matched"]
    assert assessment["lookalike_max_step_mechanics_not_verified"]
    assert assessment["lookalike_max_step_error_preserved"]
    assert assessment["programming_value_error_propagated"]


def test_small_tiled_and_untiled_hybrid_fields_are_identical() -> None:
    untiled = experiment.execute_untiled(4, "hybrid")
    tiled = experiment.execute_tiled(4)
    comparison = experiment._compare_tiled(untiled, tiled)

    assert all(comparison.values())
