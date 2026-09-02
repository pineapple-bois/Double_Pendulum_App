"""Focused tests for Experiment 019's assembled boundary."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np


EXPERIMENT_ROOT = Path(__file__).resolve().parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

import assembled_map_scale_validation as experiment

from hdf5_field_store import CellState

from development.chaos_content.prototypes.lyapunov_exponents.hybrid import (
    HYBRID_FAST_ERROR_EVALUATOR,
    HYBRID_FAST_EVALUATOR,
)
from development.chaos_content.prototypes.state_space_fields import (
    EvaluationStatus,
    ScalarEvaluation,
)


def test_resolution_and_oracle_selection_are_mechanical() -> None:
    assert experiment.SAMPLES_PER_AXIS == 64
    assert experiment.TILE_SHAPE == experiment.work_units.TileShape(8, 8)
    assert experiment.MAXIMUM_CELLS_PER_POOL == 1024
    assert experiment.INTERRUPT_AFTER_COMPLETED_TILES == 20
    assert experiment.ORACLE_AXIS_INDICES == (0, 32, 63)
    assert experiment.ORACLE_CELL_INDICES == tuple(
        (theta2, theta1)
        for theta2 in (0, 32, 63)
        for theta1 in (0, 32, 63)
    )


def test_periodic_plan_and_task_coordinates_preserve_orientation() -> None:
    context = experiment.periodic_context()
    plan = experiment.tile_plan(context)
    definition = experiment.field_definition(context)

    assert context.shape == (64, 64)
    assert len(plan) == 64
    assert experiment.work_units.validate_tile_plan(context, plan)["accepted"]
    assert context.theta1_axis[0] == -np.pi
    assert context.theta2_axis[0] == -np.pi
    assert np.pi not in context.theta1_axis
    assert np.pi not in context.theta2_axis
    final_tasks = experiment.tasks_for_tile(plan[-1])
    assert final_tasks[0].theta2_index == 56
    assert final_tasks[0].theta1_index == 56
    assert final_tasks[-1].theta2_index == 63
    assert final_tasks[-1].theta1_index == 63
    assert final_tasks[-1].linear_index == 63 * 64 + 63
    assert final_tasks[-1].theta1_radians == context.theta1_axis[63]
    assert final_tasks[-1].theta2_radians == context.theta2_axis[63]
    assert definition.observable_provenance["field_consumer"] == (
        "full-periodic initial-angle field"
    )
    assert "fixture_values" not in definition.observable_provenance


def test_compaction_keeps_execution_errors_value_less_and_route_explicit() -> None:
    context = experiment.periodic_context(2)
    work_unit = experiment.tile_plan(context)[0]
    tasks = experiment.tasks_for_tile(work_unit)
    outcomes = []
    for index, task in enumerate(tasks):
        if index == 1:
            evaluation = ScalarEvaluation(
                status=EvaluationStatus.EXECUTION_ERROR,
                value=None,
                diagnostics=None,
                elapsed_seconds=0.01,
                evaluator=HYBRID_FAST_ERROR_EVALUATOR,
                error_type="ControlledError",
                error_message="controlled bounded failure",
            )
        else:
            evaluation = ScalarEvaluation(
                status=EvaluationStatus.COMPLETED_VALID,
                value=float(index),
                diagnostics=None,
                elapsed_seconds=0.01,
                evaluator=HYBRID_FAST_EVALUATOR,
            )
        outcomes.append(
            experiment.CellOutcome(
                task=task,
                evaluation=evaluation,
                worker_pid=100 + index,
                worker_peak_rss_bytes=1024,
            )
        )

    compact = experiment._compact_tile(
        0,
        work_unit,
        outcomes,
        attempt=1,
        evaluation_wall_seconds=0.04,
    )

    assert compact.values.shape == (2, 2)
    assert compact.status[0, 1] == CellState.EXECUTION_ERROR
    assert np.isnan(compact.values[0, 1])
    assert compact.execution_route[0, 1] == 3
    assert compact.status[1, 0] == CellState.COMPLETED_VALID
    assert len(compact.exceptional_cells) == 1
    assert compact.exceptional_cells[0]["theta2_index"] == 0
    assert compact.exceptional_cells[0]["theta1_index"] == 1


def test_high_resolution_extrapolation_uses_current_tile_and_lifecycle_policy() -> None:
    resources = {"effective_cells_per_second": 400.0}
    result = experiment._extrapolation(
        resources,
        dataset_bytes=100_000,
        persistence_seconds=0.64,
        tile_count=64,
    )

    assert result["target_cell_count"] == 144_000_000
    assert result["projected_tile_count"] == 2_250_000
    assert result["projected_pool_lifetimes_at_1024_cells"] == 140_625
    assert result["raw_authoritative_array_bytes"] == 1_440_000_000
    assert result["linear_wall_time_seconds_at_observed_end_to_end_throughput"] == 360_000


def test_small_process_tile_persists_one_exact_periodic_field(tmp_path: Path) -> None:
    context = experiment.periodic_context(8)
    plan = experiment.tile_plan(context)
    path = tmp_path / "smoke.h5"
    experiment.initialize_dataset(path, experiment.field_definition(context), plan)

    session = experiment.execute_pending_tiles(path, context, plan)
    assessment = experiment._field_assessment(path, context, plan)

    assert session["evaluated_cells"] == 64
    assert session["pool_count"] == 1
    assert session["all_workers_stopped"]
    assert assessment["accepted"]
    assert assessment["completed_tile_count"] == 1
    assert sum(assessment["status_counts"].values()) == 64
    assert assessment["status_counts"]["not_yet_computed"] == 0
