from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path

import h5py
import numpy as np
import pytest

from development.chaos_content.prototypes.state_space_maps.src.generation.hdf5 import (
    CellState,
    CompletedTile,
    DuplicateTileConflict,
    FieldDefinition,
    IntegrityError,
    TileState,
    assert_dataset_compatible,
    create_dataset,
    discover_resume_state,
    read_authoritative_field,
    validate_dataset,
    write_completed_tile,
)
from development.chaos_content.prototypes.state_space_maps.src.generation.work_units import (
    TileShape,
    plan_tiles,
)


def _definition() -> FieldDefinition:
    return FieldDefinition(
        theta1_axis=(-1.0, 0.0, 1.0),
        theta2_axis=(-1.0, 0.0, 1.0),
        coordinate_unit="radians",
        periodic=False,
        periodic_interval=None,
        nominal_tile_shape=(2, 2),
        observable_provenance={"name": "synthetic"},
        physical_parameters={},
        numerical_parameters={"policy": "fixed"},
        evaluator_provenance={"name": "synthetic"},
        software_provenance={"revision": "test"},
        route_vocabulary=((0, "not_yet_computed"), (1, "synthetic")),
    )


def _tile(bounds, value: float, attempt: int = 1) -> CompletedTile:
    shape = bounds.shape
    return CompletedTile(
        bounds=bounds.as_tuple,
        values=np.full(shape, value, dtype="<f8"),
        status=np.full(shape, CellState.COMPLETED_VALID, dtype=np.uint8),
        execution_route=np.ones(shape, dtype=np.uint8),
        attempt=attempt,
        evaluation_seconds=0.01,
        diagnostics={"fixture": True},
        provenance={"fixture": "persistence"},
    )


def test_create_write_reopen_incomplete_retry_and_conflict(tmp_path: Path) -> None:
    definition = _definition()
    plan = plan_tiles(definition.field_shape, TileShape(2, 2))
    path = tmp_path / "field.h5"
    create_dataset(path, definition, tuple(unit.bounds for unit in plan))
    first = _tile(plan[0].bounds, 1.0)
    second = _tile(plan[1].bounds, 2.0)

    assert write_completed_tile(path, 0, first) == "completed"
    with h5py.File(path, "r+") as output:
        output["tiles/state"][1] = np.uint8(TileState.WRITING)
        output["field/values"][0:2, 2:3] = 99.0
        output.flush()

    snapshot = read_authoritative_field(path)
    assert np.all(np.isnan(snapshot.values[0:2, 2:3]))
    assert discover_resume_state(path).writing_tile_indices == (1,)
    assert write_completed_tile(path, 1, replace(second, attempt=2)) == "completed"
    assert validate_dataset(path).accepted
    assert assert_dataset_compatible(
        path, definition, tuple(unit.bounds for unit in plan)
    ).completed_tile_indices == (0, 1)
    assert write_completed_tile(path, 0, first) == "already_complete_identical"
    with pytest.raises(DuplicateTileConflict):
        write_completed_tile(
            path,
            0,
            replace(first, values=np.full(first.values.shape, 3.0)),
        )


def test_corruption_and_resume_definition_mismatch_fail_closed(tmp_path: Path) -> None:
    definition = _definition()
    plan = plan_tiles(definition.field_shape, TileShape(2, 2))
    path = tmp_path / "field.h5"
    create_dataset(path, definition, tuple(unit.bounds for unit in plan))
    write_completed_tile(path, 0, _tile(plan[0].bounds, 1.0))
    corrupted = tmp_path / "corrupt.h5"
    shutil.copy2(path, corrupted)
    with h5py.File(corrupted, "r+") as output:
        output["field/values"][0, 0] += 1.0
        output.flush()

    assert not validate_dataset(corrupted).accepted
    with pytest.raises(IntegrityError):
        assert_dataset_compatible(
            corrupted, definition, tuple(unit.bounds for unit in plan)
        )
    with pytest.raises(IntegrityError):
        assert_dataset_compatible(
            path,
            replace(definition, numerical_parameters={"policy": "changed"}),
            tuple(unit.bounds for unit in plan),
        )
