"""Focused tests for the bounded initial-theta1 sampling strategy."""

from __future__ import annotations

import math
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from development.chaos_content.prototypes.state_space_maps.src.lyapunov import evaluation as evaluation_module
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.evaluation import evaluate_renormalized_tangent_reference
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.reference import RenormalizedTangentSpec, run_renormalized_tangent
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.sweep import Theta1SweepSpec, run_theta1_sweep
from development.chaos_content.prototypes.state_space_maps.src.state_space_fields import (
    EvaluationStatus,
    ScalarEvaluation,
)


@pytest.fixture(scope="module")
def short_sweep():
    return run_theta1_sweep(
        Theta1SweepSpec(
            theta1_degrees=(178.0, 179.0, 180.0),
            observable_spec=RenormalizedTangentSpec(duration=0.5),
        )
    )


def test_sample_order_and_theta1_substitution_are_exact(short_sweep) -> None:
    np.testing.assert_array_equal(short_sweep.theta1_degrees, [178.0, 179.0, 180.0])
    for index, sample in enumerate(short_sweep.samples):
        assert sample.index == index
        assert sample.coordinate == short_sweep.theta1_degrees[index]
        assert sample.evaluation.status is EvaluationStatus.COMPLETED_VALID


def test_sweep_midpoint_reproduces_independent_observable(short_sweep) -> None:
    base = short_sweep.spec.observable_spec
    midpoint_spec = replace(
        base,
        initial_state=replace(base.initial_state, theta1=math.radians(179.0)),
    )
    independent = run_renormalized_tangent(midpoint_spec)
    assert short_sweep.samples[1].evaluation.value == pytest.approx(
        independent.finite_time_stretching_rate,
        rel=0.0,
        abs=0.0,
    )


def test_invalid_and_execution_error_outcomes_remain_distinct() -> None:
    calls = []

    def fake_evaluator(spec):
        calls.append(spec)
        if len(calls) == 3:
            return ScalarEvaluation(
                status=EvaluationStatus.EXECUTION_ERROR,
                value=None,
                diagnostics=None,
                elapsed_seconds=0.03,
                evaluator="test_evaluator",
                error_type="RuntimeError",
                error_message="declared integration failure",
            )
        valid = len(calls) == 1
        diagnostics = SimpleNamespace(
            maximum_normalized_reference_energy_drift=(
                1.0e-10 if valid else 2.0e-7
            ),
            maximum_post_renormalization_norm_error=2.0e-16,
            solver_function_evaluations=100,
        )
        return ScalarEvaluation(
            status=(
                EvaluationStatus.COMPLETED_VALID
                if valid
                else EvaluationStatus.COMPLETED_INVALID
            ),
            value=1.0 + len(calls),
            diagnostics=diagnostics,
            elapsed_seconds=0.01 * len(calls),
            evaluator="test_evaluator",
            validity_issues=() if valid else ("energy drift exceeded limit",),
        )

    result = run_theta1_sweep(
        Theta1SweepSpec(theta1_degrees=(178.0, 179.0, 180.0)),
        evaluator=fake_evaluator,
    )

    assert [sample.evaluation.status for sample in result.samples] == [
        EvaluationStatus.COMPLETED_VALID,
        EvaluationStatus.COMPLETED_INVALID,
        EvaluationStatus.EXECUTION_ERROR,
    ]
    assert result.samples[1].evaluation.value == 3.0
    assert result.samples[1].evaluation.validity_issues == (
        "energy drift exceeded limit",
    )
    assert result.samples[2].evaluation.value is None
    assert result.samples[2].evaluation.error_type == "RuntimeError"
    assert result.samples[2].evaluation.error_message == (
        "declared integration failure"
    )
    for expected, called in zip((178.0, 179.0, 180.0), calls):
        assert math.degrees(called.initial_state.theta1) == pytest.approx(expected)
        fixed = result.spec.observable_spec.initial_state
        assert called.initial_state.theta2 == fixed.theta2
        assert called.initial_state.omega1 == fixed.omega1
        assert called.initial_state.omega2 == fixed.omega2


def test_sampling_does_not_hide_evaluator_programming_errors() -> None:
    def programming_error(_spec):
        raise ValueError("bad test specification")

    with pytest.raises(ValueError, match="bad test specification"):
        run_theta1_sweep(
            Theta1SweepSpec(theta1_degrees=(179.0,)),
            evaluator=programming_error,
        )


def test_reference_adapter_bounds_runtime_errors_only(monkeypatch) -> None:
    def numerical_error(_spec):
        raise RuntimeError("bounded numerical failure")

    monkeypatch.setattr(
        evaluation_module,
        "run_renormalized_tangent",
        numerical_error,
    )
    outcome = evaluate_renormalized_tangent_reference(RenormalizedTangentSpec())
    assert outcome.status is EvaluationStatus.EXECUTION_ERROR
    assert outcome.value is None
    assert outcome.error_type == "RuntimeError"
    assert outcome.error_message == "bounded numerical failure"

    def programming_error(_spec):
        raise ValueError("programming failure")

    monkeypatch.setattr(
        evaluation_module,
        "run_renormalized_tangent",
        programming_error,
    )
    with pytest.raises(ValueError, match="programming failure"):
        evaluate_renormalized_tangent_reference(RenormalizedTangentSpec())


def test_sweep_values_must_be_strictly_increasing() -> None:
    with pytest.raises(ValueError, match="strictly increasing"):
        Theta1SweepSpec(theta1_degrees=(179.0, 178.0))
