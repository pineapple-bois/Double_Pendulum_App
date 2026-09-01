"""Focused tests for the bounded initial-theta1 sweep apparatus."""

from __future__ import annotations

import json
import math
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pytest


STRAND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
for path in (STRAND_ROOT, REPOSITORY_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import sweep as sweep_module
from reference import RenormalizedTangentSpec, run_renormalized_tangent
from sweep import SweepSampleStatus, Theta1SweepSpec, run_theta1_sweep
from theta1_sweep import (
    DEFAULT_DATA_PATH,
    DEFAULT_FIGURE_PATH,
    DEMONSTRATION_SPEC,
    build_figure,
    save_deliverables,
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
    fixed_state = short_sweep.spec.observable_spec.initial_state
    for index, sample in enumerate(short_sweep.samples):
        assert sample.index == index
        assert sample.initial_state.theta1 == pytest.approx(
            math.radians(sample.theta1_degrees)
        )
        assert sample.initial_state.theta2 == fixed_state.theta2
        assert sample.initial_state.omega1 == fixed_state.omega1
        assert sample.initial_state.omega2 == fixed_state.omega2
        assert sample.status is SweepSampleStatus.COMPLETED_VALID


def test_sweep_midpoint_reproduces_independent_observable(short_sweep) -> None:
    base = short_sweep.spec.observable_spec
    midpoint_spec = replace(
        base,
        initial_state=replace(base.initial_state, theta1=math.radians(179.0)),
    )
    independent = run_renormalized_tangent(midpoint_spec)
    assert short_sweep.samples[1].finite_time_stretching_rate == pytest.approx(
        independent.finite_time_stretching_rate,
        rel=0.0,
        abs=0.0,
    )


def test_invalid_and_execution_error_samples_remain_distinct(monkeypatch) -> None:
    calls = []

    def fake_evaluator(spec):
        calls.append(spec)
        if len(calls) == 3:
            raise RuntimeError("declared integration failure")
        valid = len(calls) == 1
        diagnostics = SimpleNamespace(
            numerically_valid=valid,
            validity_issues=() if valid else ("energy drift exceeded limit",),
            maximum_normalized_reference_energy_drift=1.0e-10 if valid else 2.0e-7,
            maximum_post_renormalization_norm_error=2.0e-16,
            solver_function_evaluations=100,
        )
        return SimpleNamespace(
            finite_time_stretching_rate=1.0 + len(calls),
            diagnostics=diagnostics,
        )

    monkeypatch.setattr(sweep_module, "run_renormalized_tangent", fake_evaluator)
    result = run_theta1_sweep(
        Theta1SweepSpec(theta1_degrees=(178.0, 179.0, 180.0))
    )

    assert [sample.status for sample in result.samples] == [
        SweepSampleStatus.COMPLETED_VALID,
        SweepSampleStatus.COMPLETED_INVALID,
        SweepSampleStatus.EXECUTION_ERROR,
    ]
    assert result.samples[1].finite_time_stretching_rate == 3.0
    assert result.samples[1].validity_issues == ("energy drift exceeded limit",)
    assert result.samples[2].finite_time_stretching_rate is None
    assert result.samples[2].error_type == "RuntimeError"
    assert result.samples[2].error_message == "declared integration failure"
    for expected, called in zip((178.0, 179.0, 180.0), calls):
        assert math.degrees(called.initial_state.theta1) == pytest.approx(expected)


def test_non_numerical_exceptions_are_not_hidden(monkeypatch) -> None:
    def programming_error(_spec):
        raise ValueError("bad test specification")

    monkeypatch.setattr(sweep_module, "run_renormalized_tangent", programming_error)
    with pytest.raises(ValueError, match="bad test specification"):
        run_theta1_sweep(Theta1SweepSpec(theta1_degrees=(179.0,)))


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
    assert [sample["status"] for sample in payload["samples"]] == [
        "completed_valid",
        "completed_valid",
        "completed_valid",
    ]


def test_demonstration_definition_and_output_paths_are_bounded_and_local() -> None:
    assert len(DEMONSTRATION_SPEC.theta1_degrees) == 15
    assert DEMONSTRATION_SPEC.theta1_degrees[0] == 169.0
    assert DEMONSTRATION_SPEC.theta1_degrees[7] == 179.0
    assert DEMONSTRATION_SPEC.theta1_degrees[-1] == 189.0
    assert DEMONSTRATION_SPEC.observable_spec == RenormalizedTangentSpec()
    assert DEFAULT_FIGURE_PATH == STRAND_ROOT / "outputs" / "theta1_finite_time_sweep.png"
    assert DEFAULT_DATA_PATH == STRAND_ROOT / "outputs" / "theta1_finite_time_sweep.json"


def test_sweep_values_must_be_strictly_increasing() -> None:
    with pytest.raises(ValueError, match="strictly increasing"):
        Theta1SweepSpec(theta1_degrees=(179.0, 178.0))
