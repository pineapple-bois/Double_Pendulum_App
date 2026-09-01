"""Focused equivalence tests for the Numba augmented-state RHS path."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest


STRAND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
for path in (STRAND_ROOT, REPOSITORY_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import compiled as compiled_module
from compiled import (
    COMPILED_EVALUATOR,
    compiled_reference_and_tangent_rhs,
    evaluate_renormalized_tangent_compiled,
    run_renormalized_tangent_compiled,
)
from compiled_equivalence import (
    CYCLE_LOG_ABSOLUTE_TOLERANCE,
    ENERGY_DIAGNOSTIC_ABSOLUTE_TOLERANCE,
    FINAL_REFERENCE_DISTANCE_TOLERANCE,
    FINAL_TANGENT_DISTANCE_TOLERANCE,
    RATE_ABSOLUTE_TOLERANCE,
    VALIDATION_ANGLE_PAIRS_DEGREES,
    compare_results,
    validation_spec,
)
from evaluation import evaluate_renormalized_tangent_reference
from grid import Theta1Theta2GridSpec, run_theta1_theta2_grid
from reference import (
    EulerLagrangeDynamics,
    PendulumParameters,
    RenormalizedTangentSpec,
    run_renormalized_tangent,
)
from development.chaos_content.prototypes.state_space_fields import EvaluationStatus


@pytest.fixture(scope="module")
def equivalence_comparisons():
    results = []
    for angle_pair in VALIDATION_ANGLE_PAIRS_DEGREES:
        spec = validation_spec(*angle_pair)
        reference = run_renormalized_tangent(spec)
        compiled = run_renormalized_tangent_compiled(spec)
        results.append(
            (
                angle_pair,
                reference,
                compiled,
                compare_results(reference, compiled),
            )
        )
    return results


@pytest.mark.parametrize(
    ("parameters", "augmented"),
    [
        (
            PendulumParameters(),
            np.asarray([0.73, -1.21, 2.4, -3.1, 0.3, -0.4, 0.5, -0.7]),
        ),
        (
            PendulumParameters(
                length1=0.8,
                length2=1.2,
                mass1=1.3,
                mass2=0.7,
                gravity=9.7,
            ),
            np.asarray([-2.1, 1.4, -0.8, 1.7, -0.2, 0.6, 0.4, -0.9]),
        ),
    ],
)
def test_compiled_rhs_matches_symbolic_flow_and_jacobian_vector_product(
    parameters,
    augmented,
) -> None:
    dynamics = EulerLagrangeDynamics(parameters)
    expected = dynamics.reference_and_tangent_rhs(0.37, augmented)
    actual = compiled_reference_and_tangent_rhs(
        0.37,
        augmented,
        parameters.length1,
        parameters.length2,
        parameters.mass1,
        parameters.mass2,
        parameters.gravity,
    )
    np.testing.assert_allclose(actual, expected, rtol=0.0, atol=5.0e-13)
    assert compiled_reference_and_tangent_rhs.nopython_signatures


def test_predeclared_validation_set_is_mechanical_center_plus_corners() -> None:
    assert VALIDATION_ANGLE_PAIRS_DEGREES == (
        (179.0, 179.0),
        (169.0, 169.0),
        (169.0, 189.0),
        (189.0, 169.0),
        (189.0, 189.0),
    )
    assert RATE_ABSOLUTE_TOLERANCE == 1.0e-8
    assert CYCLE_LOG_ABSOLUTE_TOLERANCE == 5.0e-8
    assert FINAL_REFERENCE_DISTANCE_TOLERANCE == 1.0e-7
    assert FINAL_TANGENT_DISTANCE_TOLERANCE == 1.0e-7
    assert ENERGY_DIAGNOSTIC_ABSOLUTE_TOLERANCE == 1.0e-8


def test_compiled_observable_meets_all_predeclared_equivalence_tolerances(
    equivalence_comparisons,
) -> None:
    for angle_pair, reference, compiled, comparison in equivalence_comparisons:
        assert comparison["accepted"], angle_pair
        assert reference.spec == compiled.spec
        np.testing.assert_array_equal(
            reference.cycle_end_time,
            compiled.cycle_end_time,
        )
        assert (
            reference.diagnostics.max_step_seconds
            == compiled.diagnostics.max_step_seconds
        )
        assert (
            reference.diagnostics.segment_count
            == compiled.diagnostics.segment_count
        )


def test_evaluator_status_and_provenance_match_for_valid_result() -> None:
    spec = RenormalizedTangentSpec(duration=0.25)
    reference = evaluate_renormalized_tangent_reference(spec)
    compiled = evaluate_renormalized_tangent_compiled(spec)

    assert reference.status is compiled.status is EvaluationStatus.COMPLETED_VALID
    assert compiled.evaluator == COMPILED_EVALUATOR
    assert compiled.value == pytest.approx(
        reference.value,
        rel=0.0,
        abs=RATE_ABSOLUTE_TOLERANCE,
    )


def test_evaluator_status_matches_for_declared_numerical_invalidity() -> None:
    spec = RenormalizedTangentSpec(
        duration=0.25,
        energy_drift_limit=1.0e-20,
    )
    reference = evaluate_renormalized_tangent_reference(spec)
    compiled = evaluate_renormalized_tangent_compiled(spec)

    assert reference.status is EvaluationStatus.COMPLETED_INVALID
    assert compiled.status is reference.status
    assert compiled.validity_issues == reference.validity_issues
    assert compiled.value == pytest.approx(
        reference.value,
        rel=0.0,
        abs=RATE_ABSOLUTE_TOLERANCE,
    )


def test_compiled_adapter_bounds_runtime_errors_only(monkeypatch) -> None:
    def numerical_error(_spec):
        raise RuntimeError("compiled integration failed")

    monkeypatch.setattr(
        compiled_module,
        "run_renormalized_tangent_compiled",
        numerical_error,
    )
    outcome = evaluate_renormalized_tangent_compiled(RenormalizedTangentSpec())
    assert outcome.status is EvaluationStatus.EXECUTION_ERROR
    assert outcome.error_type == "RuntimeError"
    assert outcome.error_message == "compiled integration failed"

    def programming_error(_spec):
        raise ValueError("compiled specification defect")

    monkeypatch.setattr(
        compiled_module,
        "run_renormalized_tangent_compiled",
        programming_error,
    )
    with pytest.raises(ValueError, match="compiled specification defect"):
        evaluate_renormalized_tangent_compiled(RenormalizedTangentSpec())


def test_compiled_evaluator_composes_with_existing_rectangular_sampling() -> None:
    spec = Theta1Theta2GridSpec(
        theta1_degrees=(178.0, 180.0),
        theta2_degrees=(178.0, 180.0),
        observable_spec=RenormalizedTangentSpec(duration=0.25),
    )
    grid = run_theta1_theta2_grid(
        spec,
        evaluator=evaluate_renormalized_tangent_compiled,
    )

    assert grid.shape == (2, 2)
    assert np.all(grid.valid_mask)
    assert {
        cell.evaluation.evaluator for row in grid.cells for cell in row
    } == {COMPILED_EVALUATOR}
    independent_spec = replace(
        spec.observable_spec,
        initial_state=replace(
            spec.observable_spec.initial_state,
            theta1=np.deg2rad(180.0),
            theta2=np.deg2rad(180.0),
        ),
    )
    independent = run_renormalized_tangent_compiled(independent_spec)
    assert grid.values[1, 1] == pytest.approx(
        independent.finite_time_stretching_rate,
        rel=0.0,
        abs=0.0,
    )
