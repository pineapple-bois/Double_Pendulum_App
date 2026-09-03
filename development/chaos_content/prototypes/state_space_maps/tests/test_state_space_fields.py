"""Tests for the earned cross-observable state-space field contracts."""

from __future__ import annotations

import math

import numpy as np
import pytest


from development.chaos_content.prototypes.state_space_maps.src.lyapunov.grid import (
    Theta1Theta2GridSpec,
)
from development.chaos_content.prototypes.state_space_maps.src.state_space_fields import (
    EvaluationStatus,
    PeriodicAngularDomain,
    SampleAxis,
    ScalarEvaluation,
    full_periodic_angle_axis,
    sample_line,
    sample_rectangle,
)


def _valid_evaluation(value: float) -> ScalarEvaluation[dict[str, float]]:
    return ScalarEvaluation(
        status=EvaluationStatus.COMPLETED_VALID,
        value=value,
        diagnostics={"value": value},
        elapsed_seconds=0.001,
        evaluator="test_reference",
    )


def test_neutral_line_sampling_preserves_axis_order_and_outcomes() -> None:
    axis = SampleAxis("energy", "joules", (1.0, 2.0, 4.0))
    result = sample_line(axis, lambda coordinate: _valid_evaluation(2.0 * coordinate))

    assert result.axis == axis
    assert [sample.index for sample in result.samples] == [0, 1, 2]
    assert [sample.coordinate for sample in result.samples] == [1.0, 2.0, 4.0]
    np.testing.assert_array_equal(result.values, [2.0, 4.0, 8.0])
    np.testing.assert_array_equal(result.valid_mask, [True, True, True])


def test_neutral_rectangle_uses_y_rows_and_x_columns() -> None:
    x_axis = SampleAxis("theta1", "radians", (-1.0, 0.0, 1.0))
    y_axis = SampleAxis("theta2", "radians", (-2.0, 2.0))
    calls = []

    def evaluate(x_coordinate: float, y_coordinate: float):
        calls.append((x_coordinate, y_coordinate))
        return _valid_evaluation(10.0 * y_coordinate + x_coordinate)

    result = sample_rectangle(x_axis, y_axis, evaluate)

    assert result.shape == (2, 3)
    assert calls == [
        (-1.0, -2.0),
        (0.0, -2.0),
        (1.0, -2.0),
        (-1.0, 2.0),
        (0.0, 2.0),
        (1.0, 2.0),
    ]
    np.testing.assert_array_equal(
        result.values,
        [[-21.0, -20.0, -19.0], [19.0, 20.0, 21.0]],
    )
    cell = result.cells[1][2]
    assert (cell.y_index, cell.x_index) == (1, 2)
    assert (cell.y_coordinate, cell.x_coordinate) == (2.0, 1.0)


def test_neutral_sampling_propagates_untranslated_evaluator_errors() -> None:
    def programming_error(_coordinate):
        raise ValueError("bad observable specification")

    with pytest.raises(ValueError, match="bad observable specification"):
        sample_line(SampleAxis("x", "unit", (0.0,)), programming_error)


def test_full_periodic_axis_uses_canonical_half_open_coordinates() -> None:
    axis = full_periodic_angle_axis(4)
    np.testing.assert_allclose(
        axis,
        [-math.pi, -0.5 * math.pi, 0.0, 0.5 * math.pi],
        rtol=0.0,
        atol=1.0e-15,
    )
    assert axis[0] == -math.pi
    assert np.all(axis < math.pi)
    assert math.pi not in axis
    assert len(np.unique(axis)) == 4


@pytest.mark.parametrize("samples", [3, 8, 32])
def test_multiple_resolutions_follow_the_declared_formula(samples) -> None:
    axis = full_periodic_angle_axis(samples)
    expected = np.asarray(
        [-math.pi + 2.0 * math.pi * index / samples for index in range(samples)]
    )
    assert axis.shape == (samples,)
    np.testing.assert_allclose(axis, expected, rtol=0.0, atol=2.0e-15)
    assert axis[-1] == pytest.approx(math.pi - 2.0 * math.pi / samples)
    assert axis[-1] < math.pi


def test_periodic_domain_supports_square_and_independent_resolutions() -> None:
    square = PeriodicAngularDomain.square(samples_per_axis=32)
    assert square.resolution == (32, 32)
    assert square.field_shape == (32, 32)

    rectangular = PeriodicAngularDomain(theta1_samples=5, theta2_samples=7)
    assert rectangular.resolution == (5, 7)
    assert rectangular.field_shape == (7, 5)
    assert rectangular.theta1_axis_radians.shape == (5,)
    assert rectangular.theta2_axis_radians.shape == (7,)


def test_periodic_domain_converts_to_existing_grid_without_endpoint_duplication() -> None:
    domain = PeriodicAngularDomain(theta1_samples=4, theta2_samples=2)
    grid = Theta1Theta2GridSpec.from_periodic_domain(domain)

    assert grid.shape == (2, 4)
    np.testing.assert_allclose(grid.theta1_degrees, [-180.0, -90.0, 0.0, 90.0])
    np.testing.assert_allclose(grid.theta2_degrees, [-180.0, 0.0])
    assert 180.0 not in grid.theta1_degrees
    assert 180.0 not in grid.theta2_degrees


@pytest.mark.parametrize("samples", [0, -1, 2.5, True])
def test_periodic_sample_counts_must_be_positive_integers(samples) -> None:
    with pytest.raises(ValueError, match="positive integer sample count"):
        full_periodic_angle_axis(samples)


def test_neutral_scalar_evaluation_enforces_status_semantics() -> None:
    valid = ScalarEvaluation(
        status=EvaluationStatus.COMPLETED_VALID,
        value=1.25,
        diagnostics={"energy_drift": 1.0e-10},
        elapsed_seconds=0.4,
        evaluator="reference",
    )
    assert valid.completed
    assert valid.numerically_valid

    invalid = ScalarEvaluation(
        status=EvaluationStatus.COMPLETED_INVALID,
        value=1.25,
        diagnostics={"energy_drift": 2.0e-7},
        elapsed_seconds=0.4,
        evaluator="reference",
        validity_issues=("energy drift exceeded limit",),
    )
    assert invalid.completed
    assert not invalid.numerically_valid

    failed = ScalarEvaluation(
        status=EvaluationStatus.EXECUTION_ERROR,
        value=None,
        diagnostics=None,
        elapsed_seconds=0.2,
        evaluator="reference",
        error_type="RuntimeError",
        error_message="integration failed",
    )
    assert not failed.completed
    assert not failed.numerically_valid

    with pytest.raises(ValueError, match="needs a value"):
        ScalarEvaluation(
            status=EvaluationStatus.COMPLETED_VALID,
            value=None,
            diagnostics=None,
            elapsed_seconds=0.1,
            evaluator="reference",
        )
