"""Regression coverage for the targeted compiled-DOP853 fallback policy."""

from __future__ import annotations


import numpy as np
import pytest


from development.chaos_content.prototypes.state_space_maps.src.lyapunov import hybrid as hybrid_module
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.compiled import evaluate_renormalized_tangent_compiled
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.compiled_equivalence import VALIDATION_ANGLE_PAIRS_DEGREES, validation_spec
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.compiled_dop853 import evaluate_renormalized_tangent_compiled_dop853
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.grid import Theta1Theta2GridSpec, run_theta1_theta2_grid
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.hybrid import (
    HYBRID_FALLBACK_EVALUATOR,
    HYBRID_FAST_ERROR_EVALUATOR,
    HYBRID_FAST_EVALUATOR,
    evaluate_renormalized_tangent_hybrid,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.reference import EulerLagrangeState, RenormalizedTangentSpec
from development.chaos_content.prototypes.state_space_maps.src.state_space_fields import (
    EvaluationStatus,
    ScalarEvaluation,
)


AUDITED_CASES = (
    (177.75, 170.25, True),
    (176.5, 170.25, False),
    (181.5, 170.66666666666666, True),
    (180.66666666666666, 170.66666666666666, False),
)


def _spec(theta1_degrees: float, theta2_degrees: float) -> RenormalizedTangentSpec:
    return RenormalizedTangentSpec(
        initial_state=EulerLagrangeState.from_degrees(
            theta1_degrees,
            theta2_degrees,
            0.0,
            0.0,
        )
    )


@pytest.mark.parametrize(
    "theta1_degrees,theta2_degrees,expects_fallback",
    AUDITED_CASES,
)
def test_audited_failures_fallback_and_neighbors_stay_fast(
    theta1_degrees: float,
    theta2_degrees: float,
    expects_fallback: bool,
) -> None:
    spec = _spec(theta1_degrees, theta2_degrees)
    fast = evaluate_renormalized_tangent_compiled_dop853(spec)
    hybrid = evaluate_renormalized_tangent_hybrid(spec)

    if expects_fallback:
        oracle = evaluate_renormalized_tangent_compiled(spec)
        assert fast.status is EvaluationStatus.EXECUTION_ERROR
        assert hybrid.evaluator == HYBRID_FALLBACK_EVALUATOR
        assert hybrid.value == oracle.value
        assert hybrid.status is oracle.status
        assert hybrid.diagnostics == oracle.diagnostics
        assert hybrid.validity_issues == oracle.validity_issues
        assert hybrid.error_type == oracle.error_type
        assert hybrid.error_message == oracle.error_message
    else:
        assert fast.status is EvaluationStatus.COMPLETED_VALID
        assert hybrid.evaluator == HYBRID_FAST_EVALUATOR
        assert hybrid.value == fast.value
        assert hybrid.status is fast.status
        assert hybrid.diagnostics == fast.diagnostics
        assert hybrid.validity_issues == fast.validity_issues


def test_experiment_015_fixtures_remain_unchanged_on_fast_path() -> None:
    for angle_pair in VALIDATION_ANGLE_PAIRS_DEGREES:
        spec = validation_spec(*angle_pair)
        fast = evaluate_renormalized_tangent_compiled_dop853(spec)
        hybrid = evaluate_renormalized_tangent_hybrid(spec)

        assert fast.status is EvaluationStatus.COMPLETED_VALID
        assert hybrid.evaluator == HYBRID_FAST_EVALUATOR
        assert hybrid.value == fast.value
        assert hybrid.status is fast.status
        assert hybrid.diagnostics == fast.diagnostics
        assert hybrid.validity_issues == fast.validity_issues


@pytest.mark.parametrize(
    "message",
    (
        "controlled ordinary scalar execution error",
        "compiled DOP853 returned a non-finite or malformed state.",
        "compiled DOP853 did not reach the requested segment endpoint: 0.2 != 0.25.",
        "compiled DOP853 failed on [0.0, 0.25] with return code -2.",
    ),
)
def test_unrelated_execution_errors_do_not_trigger_fallback(
    monkeypatch: pytest.MonkeyPatch,
    message: str,
) -> None:
    error = ScalarEvaluation(
        status=EvaluationStatus.EXECUTION_ERROR,
        value=None,
        diagnostics=None,
        elapsed_seconds=0.0,
        evaluator=hybrid_module.COMPILED_DOP853_EVALUATOR,
        error_type="RuntimeError",
        error_message=message,
    )
    fallback_called = False

    def unexpected_fallback(_spec):
        nonlocal fallback_called
        fallback_called = True
        raise AssertionError("unrelated errors must not fallback")

    monkeypatch.setattr(
        hybrid_module,
        "evaluate_renormalized_tangent_compiled_dop853",
        lambda _spec: error,
    )
    monkeypatch.setattr(
        hybrid_module,
        "evaluate_renormalized_tangent_compiled",
        unexpected_fallback,
    )

    result = evaluate_renormalized_tangent_hybrid(RenormalizedTangentSpec())

    assert not fallback_called
    assert result.evaluator == HYBRID_FAST_ERROR_EVALUATOR
    assert result.status is EvaluationStatus.EXECUTION_ERROR
    assert result.error_type == error.error_type
    assert result.error_message == error.error_message


def test_unverified_lookalike_max_step_error_remains_an_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = RenormalizedTangentSpec()
    declared = hybrid_module._resolved_max_step(spec)
    error = ScalarEvaluation(
        status=EvaluationStatus.EXECUTION_ERROR,
        value=None,
        diagnostics=None,
        elapsed_seconds=0.0,
        evaluator=hybrid_module.COMPILED_DOP853_EVALUATOR,
        error_type="RuntimeError",
        error_message=(
            "compiled DOP853 exceeded the declared max_step: "
            f"{1.005 * declared} > {declared}."
        ),
    )
    monkeypatch.setattr(
        hybrid_module,
        "evaluate_renormalized_tangent_compiled_dop853",
        lambda _spec: error,
    )

    result = evaluate_renormalized_tangent_hybrid(spec)

    assert result.evaluator == HYBRID_FAST_ERROR_EVALUATOR
    assert result.status is EvaluationStatus.EXECUTION_ERROR
    assert result.error_message == error.error_message


def test_programming_value_error_still_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def programming_error(_spec):
        raise ValueError("controlled programming error")

    monkeypatch.setattr(
        hybrid_module,
        "evaluate_renormalized_tangent_compiled_dop853",
        programming_error,
    )

    with pytest.raises(ValueError, match="controlled programming error"):
        evaluate_renormalized_tangent_hybrid(RenormalizedTangentSpec())


def test_rectangle_uses_hybrid_provenance_without_changing_orientation() -> None:
    spec = Theta1Theta2GridSpec(
        theta1_degrees=(176.5, 177.75),
        theta2_degrees=(170.25, 171.5),
        observable_spec=RenormalizedTangentSpec(),
    )
    grid = run_theta1_theta2_grid(
        spec,
        evaluator=evaluate_renormalized_tangent_hybrid,
    )

    assert grid.shape == (2, 2)
    np.testing.assert_array_equal(grid.theta1_axis_degrees, (176.5, 177.75))
    np.testing.assert_array_equal(grid.theta2_axis_degrees, (170.25, 171.5))
    assert grid.cells[0][1].x_coordinate == 177.75
    assert grid.cells[0][1].y_coordinate == 170.25
    assert grid.cells[0][1].evaluation.evaluator == HYBRID_FALLBACK_EVALUATOR
    assert grid.values[0, 1] == evaluate_renormalized_tangent_compiled(
        _spec(177.75, 170.25)
    ).value
    assert np.all(np.isfinite(grid.values))
