"""Focused persistence and field-binding tests for first-flip time."""

from __future__ import annotations

import math
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from development.chaos_content.prototypes.state_space_maps.runners.generate_first_flip_periodic_field import (
    build_manifest,
)
from development.chaos_content.prototypes.state_space_maps.src.first_flip.field_adapter import (
    FIRST_FLIP_REFERENCE_EVALUATOR,
    FirstFlipFieldSpec,
    adapt_first_flip_result,
    evaluate_first_flip_field_cell,
    initialize_first_flip_field_worker,
    periodic_first_flip_field_definition,
    run_periodic_first_flip_field,
    summarize_persisted_first_flip_field,
    validate_first_flip_reference_spots,
)
from development.chaos_content.prototypes.state_space_maps.src.first_flip.reference import (
    FirstFlipStatus,
    first_flip_time,
)
from development.chaos_content.prototypes.state_space_maps.src.generation import (
    CellState,
    IntegrityError,
    ScalarCellTask,
    accepted_process_execution_spec,
    read_authoritative_field,
)
from development.chaos_content.prototypes.state_space_maps.src.state_space_fields import (
    EvaluationStatus,
)


def _task(theta1_degrees: float, theta2_degrees: float) -> ScalarCellTask:
    return ScalarCellTask(
        linear_index=0,
        theta2_index=0,
        theta1_index=0,
        theta2_coordinate=math.radians(theta2_degrees),
        theta1_coordinate=math.radians(theta1_degrees),
    )


def test_adapter_converts_observed_and_censored_results_without_conflation() -> None:
    spec = FirstFlipFieldSpec(observation_horizon_seconds=5.0)
    initialize_first_flip_field_worker(spec)
    observed = evaluate_first_flip_field_cell(_task(-150.0, -150.0))
    censored = evaluate_first_flip_field_cell(_task(0.0, 0.0))

    assert observed.status is EvaluationStatus.COMPLETED_VALID
    assert observed.value is not None
    assert observed.value < spec.dimensionless_observation_horizon
    assert observed.diagnostics is not None
    assert observed.diagnostics.outcome == "event_observed"
    assert observed.diagnostics.event_identity == "arm1+"

    assert censored.status is EvaluationStatus.COMPLETED_VALID
    assert censored.value == spec.dimensionless_observation_horizon
    assert censored.diagnostics is not None
    assert censored.diagnostics.outcome == "right_censored"
    assert censored.diagnostics.event_time_seconds is None


def test_adapter_keeps_numerical_failure_separate_from_censoring() -> None:
    spec = FirstFlipFieldSpec(observation_horizon_seconds=1.0)
    reference = first_flip_time((0.0, 0.0, 0.0, 0.0), observation_horizon=1.0)
    solver_failure = replace(
        reference,
        status=FirstFlipStatus.SOLVER_FAILURE,
        solver_success=False,
        numerically_valid=False,
        censored=False,
        solver_message="synthetic bounded failure",
    )
    invalid = replace(
        reference,
        status=FirstFlipStatus.INVALID_INTEGRATION,
        numerically_valid=False,
        censored=False,
        validation_issues=("synthetic_invalid_state",),
    )

    failed_evaluation = adapt_first_flip_result(solver_failure, spec)
    invalid_evaluation = adapt_first_flip_result(invalid, spec)

    assert failed_evaluation.status is EvaluationStatus.EXECUTION_ERROR
    assert failed_evaluation.value is None
    assert failed_evaluation.error_type == "FirstFlipSolverFailure"
    assert invalid_evaluation.status is EvaluationStatus.COMPLETED_INVALID
    assert invalid_evaluation.value is None
    assert invalid_evaluation.validity_issues == ("synthetic_invalid_state",)


def test_field_definition_preserves_periodic_orientation_and_censor_contract() -> None:
    spec = FirstFlipFieldSpec(observation_horizon_seconds=2.0)
    definition = periodic_first_flip_field_definition(4, spec)

    assert definition.field_shape == (4, 4)
    assert definition.theta1_axis == pytest.approx(
        (-math.pi, -math.pi / 2.0, 0.0, math.pi / 2.0)
    )
    assert definition.theta2_axis == definition.theta1_axis
    assert definition.periodic_interval == "[-pi, pi)"
    assert definition.numerical_parameters["initial_angular_velocities_radians_per_second"] == [0.0, 0.0]
    assert definition.numerical_parameters["dimensionless_observation_horizon"] == pytest.approx(
        spec.dimensionless_observation_horizon
    )
    assert "right-censored" in definition.observable_provenance["censoring_contract"]


def test_tiny_field_is_deterministic_persisted_and_resumable(tmp_path: Path) -> None:
    path = tmp_path / "first_flip_2x2.h5"
    spec = FirstFlipFieldSpec(observation_horizon_seconds=2.0)
    created = run_periodic_first_flip_field(path, 2, mode="create", spec=spec)
    first = read_authoritative_field(path)
    field_summary = summarize_persisted_first_flip_field(path)
    spots = validate_first_flip_reference_spots(path, spec)
    resumed = run_periodic_first_flip_field(path, 2, mode="resume", spec=spec)
    second = read_authoritative_field(path)

    assert created.validation.accepted
    assert created.evaluated_cells == 4
    assert np.all(first.status == CellState.COMPLETED_VALID)
    assert np.all(np.isfinite(first.values))
    assert np.all(first.values <= spec.dimensionless_observation_horizon)
    assert field_summary.observed_count + field_summary.censored_count == 4
    assert field_summary.completed_invalid_count == 0
    assert field_summary.execution_error_count == 0
    assert spots.accepted
    assert len(spots.selected_indices) == 4
    assert spots.maximum_event_time_difference_seconds <= 5.0e-8
    manifest = build_manifest(
        output_path=path,
        definition=periodic_first_flip_field_definition(2, spec),
        execution=accepted_process_execution_spec(),
        run_summary=created,
        field_summary=field_summary,
        spot_validation=spots,
        completed_at_utc="2026-09-05T00:00:00+00:00",
        operation_wall_seconds=created.total_seconds,
    )
    assert manifest["scientific_contract"]["numerical_parameters"][
        "observation_horizon_seconds"
    ] == 2.0
    assert manifest["scientific_contract"]["numerical_parameters"][
        "dimensionless_observation_horizon"
    ] == pytest.approx(spec.dimensionless_observation_horizon)
    assert manifest["field_statistics"]["observation_horizon_seconds"] == 2.0
    assert manifest["field_statistics"]["observed_count"] == field_summary.observed_count
    assert manifest["field_statistics"]["censored_count"] == field_summary.censored_count
    assert resumed.validation.accepted
    assert resumed.evaluated_cells == 0
    assert resumed.preexisting_completed_cells == 4
    assert np.array_equal(first.values, second.values)
    assert np.array_equal(first.status, second.status)
    assert np.array_equal(first.execution_route, second.execution_route)
    assert set(np.unique(first.execution_route)) == {1}
    assert (
        first.metadata["execution_route_vocabulary"]["1"]
        == FIRST_FLIP_REFERENCE_EVALUATOR
    )
    with pytest.raises(IntegrityError):
        run_periodic_first_flip_field(
            path,
            2,
            mode="resume",
            spec=FirstFlipFieldSpec(observation_horizon_seconds=3.0),
        )
