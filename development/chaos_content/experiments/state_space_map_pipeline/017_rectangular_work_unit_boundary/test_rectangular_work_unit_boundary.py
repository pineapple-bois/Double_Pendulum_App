"""Focused correctness tests for Experiment 017's work-unit boundary."""

from __future__ import annotations

import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest


EXPERIMENT_ROOT = Path(__file__).resolve().parent
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

import rectangular_work_unit_boundary as experiment

from development.chaos_content.prototypes.state_space_maps.src.lyapunov.reference import (
    RenormalizedTangentSpec,
)


def test_candidate_shapes_are_the_predeclared_mechanical_set() -> None:
    assert tuple(
        (shape.theta2_cells, shape.theta1_cells)
        for shape in experiment.CANDIDATE_TILE_SHAPES
    ) == (
        (1, 1),
        (4, 4),
        (8, 8),
        (16, 16),
        (4, 16),
        (16, 4),
    )


def test_half_open_tile_mapping_and_clipped_edges_are_explicit() -> None:
    context = experiment.FieldContext(
        theta1_axis=tuple(float(index) for index in range(7)),
        theta2_axis=tuple(float(index) for index in range(5)),
        coordinate_unit="radians",
        periodic=True,
        observable_spec=None,
        evaluator="coordinate_only",
    )
    work_units = experiment.plan_tiles(context, experiment.TileShape(3, 4))

    assert [unit.bounds.shape for unit in work_units] == [
        (3, 4),
        (3, 3),
        (2, 4),
        (2, 3),
    ]
    edge = work_units[-1]
    assert edge.bounds.global_indices(0, 0) == (3, 4)
    assert edge.bounds.global_indices(1, 2) == (4, 6)
    with pytest.raises(IndexError):
        edge.bounds.global_indices(2, 0)


def test_periodic_coverage_orientation_and_endpoint_contract() -> None:
    assessment = experiment.assess_periodic_coverage()

    assert assessment["accepted"]
    assert assessment["context_shape"] == [25, 33]
    assert assessment["resolution_theta1_theta2"] == [33, 25]
    assert assessment["all_coordinates_half_open"]
    assert assessment["positive_pi_absent"]
    assert assessment["overlap_plan_rejected"]
    assert assessment["gap_plan_rejected"]
    for shape in experiment.CANDIDATE_TILE_SHAPES:
        result = assessment["shape_results"][shape.label]
        assert result["accepted"]
        assert result["total_tile_cells"] == 33 * 25
        assert result["maximum_coverage_count"] == 1
        assert result["order_independent"]
        assert result["orientation_correct"]


def test_invalid_plan_validation_detects_overlap_and_gap() -> None:
    context = experiment.periodic_coordinate_context()
    plan = experiment.plan_tiles(context, experiment.TileShape(8, 8))

    overlap = experiment.validate_tile_plan(context, plan + (plan[0],))
    gap = experiment.validate_tile_plan(context, plan[1:])

    assert not overlap["accepted"]
    assert overlap["overlapped_cell_count"] == plan[0].bounds.cell_count
    assert not gap["accepted"]
    assert gap["missing_cell_count"] == plan[0].bounds.cell_count


def test_compact_result_preserves_value_status_and_sparse_details() -> None:
    context = experiment.FieldContext(
        theta1_axis=(0.0, 1.0, 2.0, 3.0),
        theta2_axis=(0.0, 1.0, 2.0, 3.0),
        coordinate_unit="degrees",
        periodic=False,
        observable_spec=replace(RenormalizedTangentSpec(), duration=0.25),
        evaluator="synthetic",
    )
    unit = experiment.plan_tiles(context, experiment.TileShape(2, 2))[0]
    compact = experiment._compact_tile(
        unit,
        experiment._synthetic_outcomes(unit),
        attempt=1,
        execution_wall_seconds=0.0,
    )

    assert compact.status_counts == (2, 1, 1)
    assert compact.values[0, 1] == 1.0
    assert math.isnan(compact.values[1, 0])
    np.testing.assert_array_equal(compact.status_codes, [[0, 1], [2, 0]])
    assert [item.status for item in compact.exceptional_cells] == [
        "completed_invalid",
        "execution_error",
    ]
    assert compact.exceptional_cells[0].validity_issues == (
        "controlled invalidity",
    )
    assert compact.exceptional_cells[1].error_message == (
        "controlled scalar failure"
    )


def test_failure_retry_and_interruption_semantics() -> None:
    assessment = experiment.assess_failure_retry_and_interruption()

    assert assessment["accepted"]
    assert assessment["status_counts_valid_invalid_error"] == (14, 1, 1)
    assert assessment["work_unit_failure_recorded"]
    assert assessment["failed_partial_result_absent"]
    assert assessment["unrelated_completed_tiles_unchanged"]
    assert assessment["retry_identity_and_tasks_identical"]
    assert assessment["retry_matches_clean_result"]
    assert assessment["interrupted_resume_matches_clean_result"]
    assert assessment["completed_prefix_skipped_count"] == 2
    assert assessment["programming_error_propagated"]


def test_tiled_process_execution_matches_untiled_in_both_orders() -> None:
    spec = replace(RenormalizedTangentSpec(), duration=0.25)
    context = experiment.bounded_field_context(4, spec)
    executor, identities, _startup = experiment._open_worker_pool(spec)
    try:
        outcomes, elapsed = experiment._untiled_outcomes(executor, context)
        baseline = experiment.compact_untiled_baseline(
            context, outcomes, elapsed_seconds=elapsed
        )
        tiled = experiment.execute_tiled_field(
            executor,
            context,
            experiment.TileShape(2, 2),
            outcomes,
        )
        reversed_tiled = experiment.execute_tiled_field(
            executor,
            context,
            experiment.TileShape(2, 2),
            outcomes,
            tile_order="reversed",
            local_order="reversed",
        )
    finally:
        shutdown = experiment._close_worker_pool(executor, identities)

    assert shutdown["workers_stopped"]
    assert experiment.compare_compact_fields(baseline, tiled)["accepted"]
    assert experiment.compare_compact_fields(tiled, reversed_tiled)["accepted"]
    assert tiled.equivalence["maximum_rate_error_per_second"] == 0.0
    assert tiled.equivalence["maximum_energy_diagnostic_error"] == 0.0
    assert tiled.equivalence["exact_value_matches"] == 16
    assert tiled.equivalence["exact_diagnostic_matches"] == 16


def _distribution(wall: float, spread: float = 0.05) -> dict[str, object]:
    return {
        "wall_seconds_median": wall,
        "wall_seconds_q1": wall - spread,
        "wall_seconds_q3": wall + spread,
        "all_equivalence_checks_passed": True,
    }


def test_provisional_decision_prefers_smallest_overlapping_square() -> None:
    timing_groups = {}
    for samples in experiment.NUMERICAL_SAMPLE_COUNTS:
        timing_groups.update(
            {
                f"1x1|{samples}x{samples}": _distribution(4.0),
                f"4x4|{samples}x{samples}": _distribution(1.04),
                f"8x8|{samples}x{samples}": _distribution(1.00),
                f"16x16|{samples}x{samples}": _distribution(1.01),
                f"4x16|{samples}x{samples}": _distribution(1.02),
                f"16x4|{samples}x{samples}": _distribution(1.03),
            }
        )

    decision = experiment.choose_provisional_tile(timing_groups)

    assert decision["outcome"] == "fixed_shape_provisional"
    assert decision["provisional_shape"] == "4x4"
    assert "8x8" in decision["timing_equivalent_shapes"]


def test_nonoverlapping_timings_do_not_manufacture_a_fixed_shape() -> None:
    timing_groups = {}
    for samples in experiment.NUMERICAL_SAMPLE_COUNTS:
        for index, shape in enumerate(experiment.CANDIDATE_TILE_SHAPES):
            timing_groups[f"{shape.label}|{samples}x{samples}"] = _distribution(
                1.0 + index,
                spread=0.01,
            )
        timing_groups[f"1x1|{samples}x{samples}"][
            "all_equivalence_checks_passed"
        ] = False

    decision = experiment.choose_provisional_tile(timing_groups)
    final = experiment.final_decision(
        decision,
        {"accepted": True},
        {"accepted": True},
        {"accepted": True},
        {"accepted": True, "accepted_lifecycle_policy": {}},
    )

    assert decision["outcome"] == "bounded_range_unresolved"
    assert final["outcome"] == "rejected"
    assert not final["gates"]["fixed_or_bounded_shape_selected"]
