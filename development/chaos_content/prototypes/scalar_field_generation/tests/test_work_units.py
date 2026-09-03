from __future__ import annotations

import numpy as np

from development.chaos_content.prototypes.scalar_field_generation.work_units import (
    TileShape,
    plan_tiles,
    tasks_for_work_unit,
    validate_tile_plan,
)


def test_half_open_plan_clips_edges_and_covers_field_once() -> None:
    plan = plan_tiles((5, 7), TileShape(3, 4))

    assert [unit.bounds.shape for unit in plan] == [
        (3, 4),
        (3, 3),
        (2, 4),
        (2, 3),
    ]
    assert [unit.index for unit in plan] == [0, 1, 2, 3]
    assert plan[-1].bounds.global_indices(1, 2) == (4, 6)
    coverage = validate_tile_plan((5, 7), plan)
    assert coverage.accepted
    assert coverage.planned_cell_count == 35
    assert coverage.maximum_coverage_count == 1


def test_tasks_preserve_theta2_row_theta1_column_orientation() -> None:
    theta1 = np.linspace(-3.0, 3.0, 7)
    theta2 = np.linspace(-2.0, 2.0, 5)
    work_unit = plan_tiles((5, 7), TileShape(3, 4))[-1]

    tasks = tasks_for_work_unit(work_unit, theta1, theta2)

    assert tasks[0].theta2_index == 3
    assert tasks[0].theta1_index == 4
    assert tasks[0].linear_index == 3 * 7 + 4
    assert tasks[0].theta2_coordinate == theta2[3]
    assert tasks[0].theta1_coordinate == theta1[4]
    assert tasks[-1].theta2_index == 4
    assert tasks[-1].theta1_index == 6
