"""Focused tests for the rectangular initial-angle grid apparatus."""

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

import sweep as sweep_module
from grid import Theta1Theta2GridSpec, run_theta1_theta2_grid
from reference import RenormalizedTangentSpec, run_renormalized_tangent
from sweep import SweepSampleStatus
from theta1_theta2_grid import (
    DEFAULT_DATA_PATH,
    DEFAULT_FIGURE_PATH,
    DEMONSTRATION_SPEC,
    SMOKE_SPEC,
    build_heatmap,
    load_grid_data,
    save_grid_data,
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
            assert cell.theta2_index == theta2_index
            assert cell.theta1_index == theta1_index
            assert cell.theta1_sample.initial_state.theta1 == pytest.approx(
                math.radians(short_grid.theta1_axis_degrees[theta1_index])
            )
            assert cell.theta1_sample.initial_state.theta2 == pytest.approx(
                math.radians(short_grid.theta2_axis_degrees[theta2_index])
            )
            assert cell.theta1_sample.initial_state.omega1 == 0.0
            assert cell.theta1_sample.initial_state.omega2 == 0.0


def test_one_cell_reproduces_an_independent_single_condition(short_grid) -> None:
    theta2_index, theta1_index = 1, 1
    cell = short_grid.cells[theta2_index][theta1_index]
    base = short_grid.spec.observable_spec
    independent_spec = replace(base, initial_state=cell.theta1_sample.initial_state)
    independent = run_renormalized_tangent(independent_spec)
    assert short_grid.values[theta2_index, theta1_index] == pytest.approx(
        independent.finite_time_stretching_rate,
        rel=0.0,
        abs=0.0,
    )


def test_grid_preserves_invalid_and_execution_error_cells(monkeypatch) -> None:
    calls = []

    def fake_evaluator(spec):
        calls.append(spec)
        if len(calls) == 3:
            raise RuntimeError("declared grid-cell failure")
        valid = len(calls) != 2
        diagnostics = SimpleNamespace(
            numerically_valid=valid,
            validity_issues=() if valid else ("energy drift exceeded limit",),
            maximum_normalized_reference_energy_drift=1.0e-10 if valid else 2.0e-7,
            maximum_post_renormalization_norm_error=2.0e-16,
            solver_function_evaluations=100,
        )
        return SimpleNamespace(
            finite_time_stretching_rate=float(len(calls)),
            diagnostics=diagnostics,
        )

    monkeypatch.setattr(sweep_module, "run_renormalized_tangent", fake_evaluator)
    result = run_theta1_theta2_grid(
        Theta1Theta2GridSpec(
            theta1_degrees=(178.0, 180.0),
            theta2_degrees=(177.0, 181.0),
        )
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
    assert result.cells[0][1].theta1_sample.validity_issues == (
        "energy drift exceeded limit",
    )
    assert result.cells[1][0].theta1_sample.error_message == (
        "declared grid-cell failure"
    )


def test_programming_errors_are_not_converted_to_grid_data(monkeypatch) -> None:
    def programming_error(_spec):
        raise ValueError("bad grid specification")

    monkeypatch.setattr(sweep_module, "run_renormalized_tangent", programming_error)
    with pytest.raises(ValueError, match="bad grid specification"):
        run_theta1_theta2_grid(
            Theta1Theta2GridSpec(
                theta1_degrees=(178.0, 180.0),
                theta2_degrees=(178.0, 180.0),
            )
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
