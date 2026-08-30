"""Focused tests for Experiment 008 common-reference isolation."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

EXPERIMENT_ROOT = Path(__file__).resolve().parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

import common_reference_qr_isolation as experiment


@pytest.fixture(scope="module")
def dynamics():
    return experiment.experiment006.VariationalDynamics()


@pytest.fixture(scope="module")
def short_history(dynamics):
    return experiment.build_common_reference_history(dynamics, duration=0.5)


def test_common_reference_local_refinement_and_energy_pass(short_history) -> None:
    summary = short_history.public_summary

    assert summary["accepted"]
    assert summary["segment_count"] == 4
    assert (
        summary["maximum_local_candidate_a_error"]
        <= experiment.REFERENCE_LOCAL_ERROR_LIMIT
    )
    assert (
        summary["maximum_normalized_energy_drift"]
        <= experiment.REFERENCE_ENERGY_DRIFT_LIMIT
    )


def test_common_reference_boundary_is_physically_continuous(
    dynamics, short_history
) -> None:
    boundary = experiment.REFERENCE_SEGMENT_SECONDS
    left = experiment.experiment006.canonicalize_state_angles(
        short_history.segments[0].dense_solution(boundary)
    )
    right = short_history.evaluate(boundary)
    difference = experiment.experiment006.wrapped_el_difference(left, right)

    assert experiment.experiment006.candidate_a_norm(difference) <= 1.0e-13
    np.testing.assert_allclose(
        dynamics.jacobian(left, boundary),
        dynamics.jacobian(right, boundary),
        rtol=0.0,
        atol=1.0e-12,
    )


def test_reference_queries_are_deterministic_and_range_checked(short_history) -> None:
    np.testing.assert_array_equal(
        short_history.evaluate(0.375), short_history.evaluate(0.375)
    )
    with pytest.raises(ValueError):
        short_history.evaluate(-0.1)
    with pytest.raises(ValueError):
        short_history.evaluate(0.6)


def test_tangent_rhs_uses_only_common_history(dynamics, short_history) -> None:
    tangent = np.arange(16, dtype=float).reshape(4, 4) / 7.0
    time_value = 0.31
    actual = experiment.tangent_matrix_rhs(
        dynamics, short_history, time_value, tangent.reshape(16)
    ).reshape(4, 4)
    reference = short_history.evaluate(time_value)

    np.testing.assert_allclose(
        actual,
        dynamics.jacobian(reference, time_value) @ tangent,
        rtol=0.0,
        atol=1.0e-14,
    )


def test_short_common_reference_qr_run_preserves_bookkeeping(
    dynamics, short_history
) -> None:
    run = experiment.run_common_reference_qr(
        dynamics,
        short_history,
        run_id="short_test",
        duration=0.5,
    )

    assert run["accepted"]
    assert run["cycle_count"] == 2
    cumulative = np.cumsum(run["_cycle_logs"], axis=0)
    np.testing.assert_allclose(
        cumulative,
        run["_cumulative_logs"],
        rtol=0.0,
        atol=experiment.experiment007.BOOKKEEPING_ERROR_LIMIT,
    )


def test_short_tangent_tolerance_refinement_collapses_on_common_history(
    dynamics, short_history
) -> None:
    baseline = experiment.run_common_reference_qr(
        dynamics,
        short_history,
        run_id="baseline_short",
        duration=0.5,
    )
    strict = experiment.run_common_reference_qr(
        dynamics,
        short_history,
        run_id="strict_short",
        duration=0.5,
        policy=experiment.STRICT_TANGENT_POLICY,
    )
    difference = np.max(
        np.abs(
            np.asarray(baseline["final_diagnostic_spectrum_per_second"])
            - np.asarray(strict["final_diagnostic_spectrum_per_second"])
        )
    )

    assert difference <= experiment.STRICT_DIFFERENCE_LIMIT


def _synthetic_comparison(*, accepted: bool, ratio: float) -> dict[str, float | bool]:
    return {
        "accepted_for_collapse": accepted,
        "difference_limit_per_second": 0.01,
        "final_maximum_difference_per_second": 0.02,
        "late_window_maximum_difference_per_second": 0.02,
        "final_separation_ratio": ratio,
        "late_window_separation_ratio": ratio,
    }


def test_classification_boundaries_are_predeclared_and_ternary() -> None:
    collapsed = {
        "case": _synthetic_comparison(accepted=True, ratio=0.1)
    }
    material = {
        "case": _synthetic_comparison(accepted=False, ratio=0.7)
    }
    intermediate = {
        "case": _synthetic_comparison(accepted=False, ratio=0.3)
    }

    assert experiment.classify_isolation(
        validity_accepted=True, comparisons=collapsed
    ) == "reference_shadow_divergence_primary_observed_source"
    assert experiment.classify_isolation(
        validity_accepted=True, comparisons=material
    ) == "material_tangent_or_qr_policy_dependence_remains"
    assert experiment.classify_isolation(
        validity_accepted=True, comparisons=intermediate
    ) == "isolation_numerically_unresolved"
    assert experiment.classify_isolation(
        validity_accepted=False, comparisons=collapsed
    ) == "isolation_numerically_unresolved"

