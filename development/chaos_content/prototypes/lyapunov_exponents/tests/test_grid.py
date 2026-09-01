"""Focused tests for the rectangular initial-angle sampling strategy."""

from __future__ import annotations

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

from grid import Theta1Theta2GridSpec, run_theta1_theta2_grid
from reference import RenormalizedTangentSpec, run_renormalized_tangent
from theta1_theta2_grid import (
    DEFAULT_DATA_PATH,
    DEFAULT_FIGURE_PATH,
    DEMONSTRATION_SPEC,
    SMOKE_SPEC,
    build_heatmap,
    load_grid_data,
    save_grid_data,
    save_heatmap,
)
from development.chaos_content.prototypes.state_space_fields import (
    EvaluationStatus,
    RectangularCell,
    ScalarEvaluation,
)


@pytest.fixture(scope="module")
def short_grid():
    return run_theta1_theta2_grid(
        Theta1Theta2GridSpec(
            theta1_degrees=(178.0, 179.0, 180.0),
            theta2_degrees=(178.0, 180.0),
            observable_spec=RenormalizedTangentSpec(duration=0.25),
        )
    )


def test_shape_indexing_and_both_angle_substitutions_are_explicit(short_grid) -> None:
    assert short_grid.shape == (2, 3)
    assert short_grid.values.shape == (2, 3)
    assert short_grid.statuses.shape == (2, 3)
    np.testing.assert_array_equal(short_grid.theta1_axis_degrees, [178, 179, 180])
    np.testing.assert_array_equal(short_grid.theta2_axis_degrees, [178, 180])

    for theta2_index, row in enumerate(short_grid.cells):
        for theta1_index, cell in enumerate(row):
            assert cell.y_index == theta2_index
            assert cell.x_index == theta1_index
            assert cell.x_coordinate == short_grid.theta1_axis_degrees[theta1_index]
            assert cell.y_coordinate == short_grid.theta2_axis_degrees[theta2_index]
            assert cell.evaluation.status is EvaluationStatus.COMPLETED_VALID


def test_grid_cell_is_not_a_wrapped_theta1_sweep_sample(short_grid) -> None:
    cell = short_grid.cells[0][0]
    assert isinstance(cell, RectangularCell)
    assert not hasattr(cell, "theta1_sample")
    assert not hasattr(cell, "theta1_degrees")
    assert cell.x_coordinate == short_grid.theta1_axis_degrees[0]
    assert cell.y_coordinate == short_grid.theta2_axis_degrees[0]


def test_one_cell_reproduces_an_independent_single_condition(short_grid) -> None:
    theta2_index, theta1_index = 1, 1
    cell = short_grid.cells[theta2_index][theta1_index]
    base = short_grid.spec.observable_spec
    independent_spec = replace(
        base,
        initial_state=replace(
            base.initial_state,
            theta1=math.radians(cell.x_coordinate),
            theta2=math.radians(cell.y_coordinate),
        ),
    )
    independent = run_renormalized_tangent(independent_spec)
    assert short_grid.values[theta2_index, theta1_index] == pytest.approx(
        independent.finite_time_stretching_rate,
        rel=0.0,
        abs=0.0,
    )


def test_grid_preserves_invalid_and_execution_error_outcomes() -> None:
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
                error_message="declared grid-cell failure",
            )
        valid = len(calls) != 2
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
            value=float(len(calls)),
            diagnostics=diagnostics,
            elapsed_seconds=0.01 * len(calls),
            evaluator="test_evaluator",
            validity_issues=() if valid else ("energy drift exceeded limit",),
        )

    result = run_theta1_theta2_grid(
        Theta1Theta2GridSpec(
            theta1_degrees=(178.0, 180.0),
            theta2_degrees=(177.0, 181.0),
        ),
        evaluator=fake_evaluator,
    )

    np.testing.assert_array_equal(
        result.statuses,
        [
            ["completed_valid", "completed_invalid"],
            ["execution_error", "completed_valid"],
        ],
    )
    assert result.values[0, 1] == 2.0
    assert math.isnan(result.values[1, 0])
    assert result.cells[0][1].evaluation.validity_issues == (
        "energy drift exceeded limit",
    )
    assert result.cells[1][0].evaluation.error_message == (
        "declared grid-cell failure"
    )
    expected_coordinates = [
        (178.0, 177.0),
        (180.0, 177.0),
        (178.0, 181.0),
        (180.0, 181.0),
    ]
    for called, (theta1, theta2) in zip(calls, expected_coordinates):
        assert math.degrees(called.initial_state.theta1) == pytest.approx(theta1)
        assert math.degrees(called.initial_state.theta2) == pytest.approx(theta2)
        assert called.initial_state.omega1 == 0.0
        assert called.initial_state.omega2 == 0.0


def test_grid_does_not_hide_evaluator_programming_errors() -> None:
    def programming_error(_spec):
        raise ValueError("bad grid specification")

    with pytest.raises(ValueError, match="bad grid specification"):
        run_theta1_theta2_grid(
            Theta1Theta2GridSpec(
                theta1_degrees=(178.0, 180.0),
                theta2_degrees=(178.0, 180.0),
            ),
            evaluator=programming_error,
        )


def test_persisted_field_reloads_with_identical_axes_values_and_statuses(
    short_grid, tmp_path
) -> None:
    path = save_grid_data(short_grid, tmp_path / "grid.json")
    payload = load_grid_data(path)

    assert payload["array_convention"] == (
        "values_per_second[theta2_index][theta1_index]"
    )
    assert payload["shape"] == [2, 3]
    np.testing.assert_array_equal(
        payload["theta1_axis_degrees"], short_grid.theta1_axis_degrees
    )
    np.testing.assert_array_equal(
        payload["theta2_axis_degrees"], short_grid.theta2_axis_degrees
    )
    np.testing.assert_array_equal(payload["values_per_second"], short_grid.values)
    np.testing.assert_array_equal(payload["statuses"], short_grid.statuses)
    assert {cell["evaluator"] for cell in payload["cells"]} == {
        "numpy_scipy_reference"
    }
    target = next(
        cell
        for cell in payload["cells"]
        if cell["theta2_index"] == 1 and cell["theta1_index"] == 2
    )
    assert target["theta1_degrees"] == 180.0
    assert target["theta2_degrees"] == 180.0
    assert target["initial_state_radians"]["theta1"] == pytest.approx(math.pi)
    assert target["initial_state_radians"]["theta2"] == pytest.approx(math.pi)


def test_heatmap_mesh_uses_theta1_columns_and_theta2_rows(short_grid) -> None:
    figure = build_heatmap(short_grid)
    axis = figure.axes[0]
    mesh = axis.collections[0]
    theta2_index, theta1_index = 1, 2
    coordinates = mesh.get_coordinates()
    cell_center = coordinates[
        theta2_index : theta2_index + 2,
        theta1_index : theta1_index + 2,
    ].mean(axis=(0, 1))

    np.testing.assert_allclose(
        cell_center,
        [
            short_grid.theta1_axis_degrees[theta1_index],
            short_grid.theta2_axis_degrees[theta2_index],
        ],
        rtol=0.0,
        atol=1.0e-12,
    )
    np.testing.assert_array_equal(
        np.ma.getdata(mesh.get_array()).reshape(short_grid.shape),
        short_grid.values,
    )
    assert axis.get_xlabel() == r"initial angle $\theta_1(0)$ (degrees)"
    assert axis.get_ylabel() == r"initial angle $\theta_2(0)$ (degrees)"
    plt.close(figure)


def test_heatmap_can_be_saved_without_recomputing_grid(short_grid, tmp_path) -> None:
    path = save_heatmap(short_grid, tmp_path / "grid.png")
    assert path.is_file()
    assert path.stat().st_size > 0


def test_smoke_and_demonstration_definitions_are_bounded_and_source_local() -> None:
    assert SMOKE_SPEC.shape == (4, 4)
    assert DEMONSTRATION_SPEC.shape == (9, 9)
    assert DEMONSTRATION_SPEC.theta1_degrees[0] == 169.0
    assert DEMONSTRATION_SPEC.theta1_degrees[4] == 179.0
    assert DEMONSTRATION_SPEC.theta1_degrees[-1] == 189.0
    assert DEMONSTRATION_SPEC.theta2_degrees[0] == 169.0
    assert DEMONSTRATION_SPEC.theta2_degrees[4] == 179.0
    assert DEMONSTRATION_SPEC.theta2_degrees[-1] == 189.0
    assert DEMONSTRATION_SPEC.observable_spec == RenormalizedTangentSpec()
    assert DEFAULT_DATA_PATH == STRAND_ROOT / "outputs" / "theta1_theta2_finite_time_grid.json"
    assert DEFAULT_FIGURE_PATH == STRAND_ROOT / "outputs" / "theta1_theta2_finite_time_grid.png"


def test_grid_axes_must_be_strictly_increasing() -> None:
    with pytest.raises(ValueError, match="theta2_degrees must be strictly increasing"):
        Theta1Theta2GridSpec(
            theta1_degrees=(178.0, 180.0),
            theta2_degrees=(180.0, 178.0),
        )
