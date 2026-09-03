"""Focused tests for the bounded initial-theta1 sampling strategy."""

from __future__ import annotations

import json
import math
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pytest

STATE_SPACE_MAPS_ROOT = Path(__file__).resolve().parents[2]

from development.chaos_content.prototypes.state_space_maps.src.lyapunov import evaluation as evaluation_module
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.evaluation import evaluate_renormalized_tangent_reference
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.reference import RenormalizedTangentSpec, run_renormalized_tangent
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.sweep import Theta1SweepSpec, run_theta1_sweep
from development.chaos_content.prototypes.state_space_maps.runners.render_lyapunov_theta1_sweep import (
    DEFAULT_DATA_PATH,
    DEFAULT_FIGURE_PATH,
    DEMONSTRATION_SPEC,
    build_figure,
    save_deliverables,
)
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


def test_sweep_figure_and_json_preserve_semantics(short_sweep, tmp_path) -> None:
    figure = build_figure(short_sweep)
    axis = figure.axes[0]
    assert "not asymptotic" in axis.get_title()
    assert axis.get_xlabel() == r"initial angle $\theta_1(0)$ (degrees)"
    plt.close(figure)

    figure_path = tmp_path / "sweep.png"
    data_path = tmp_path / "sweep.json"
    save_deliverables(
        short_sweep,
        figure_path=figure_path,
        data_path=data_path,
    )
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    assert figure_path.is_file()
    assert payload["asymptotic_convergence_claimed"] is False
    assert payload["sweep_coordinate"] == "theta1"
    assert payload["timing"]["sample_count"] == 3
    assert payload["samples"][1]["theta1_degrees"] == 179.0
    assert payload["samples"][1]["initial_state_radians"]["theta1"] == pytest.approx(
        math.radians(179.0)
    )
    assert [sample["status"] for sample in payload["samples"]] == [
        "completed_valid",
        "completed_valid",
        "completed_valid",
    ]
    assert {sample["evaluator"] for sample in payload["samples"]} == {
        "numpy_scipy_reference"
    }


def test_demonstration_definition_and_output_paths_are_bounded_and_local() -> None:
    assert len(DEMONSTRATION_SPEC.theta1_degrees) == 15
    assert DEMONSTRATION_SPEC.theta1_degrees[0] == 169.0
    assert DEMONSTRATION_SPEC.theta1_degrees[7] == 179.0
    assert DEMONSTRATION_SPEC.theta1_degrees[-1] == 189.0
    assert DEMONSTRATION_SPEC.observable_spec == RenormalizedTangentSpec()
    assert DEFAULT_FIGURE_PATH == (
        STATE_SPACE_MAPS_ROOT
        / "outputs"
        / "lyapunov"
        / "theta1_finite_time_sweep.png"
    )
    assert DEFAULT_DATA_PATH == (
        STATE_SPACE_MAPS_ROOT
        / "outputs"
        / "lyapunov"
        / "theta1_finite_time_sweep.json"
    )


def test_sweep_values_must_be_strictly_increasing() -> None:
    with pytest.raises(ValueError, match="strictly increasing"):
        Theta1SweepSpec(theta1_degrees=(179.0, 178.0))
