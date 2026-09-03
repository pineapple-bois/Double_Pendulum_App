from __future__ import annotations

import shutil
from pathlib import Path

import h5py
import numpy as np
import pytest

from development.chaos_content.prototypes.state_space_maps.src.generation import (
    EvaluatorBinding,
    FieldDefinition,
    ProcessExecutionSpec,
    TileState,
    discover_resume_state,
    read_authoritative_field,
    run_scalar_field,
)
from . import worker_fixture


def _definition() -> FieldDefinition:
    return FieldDefinition(
        theta1_axis=(-2.0, -1.0, 0.0, 1.0, 2.0),
        theta2_axis=(-1.0, 0.0, 1.0),
        coordinate_unit="radians",
        periodic=False,
        periodic_interval=None,
        nominal_tile_shape=(2, 2),
        observable_provenance={"name": "synthetic"},
        physical_parameters={},
        numerical_parameters={"offset": 0.25},
        evaluator_provenance={"binding": "synthetic"},
        software_provenance={"revision": "test"},
        route_vocabulary=((0, "not_yet_computed"), (1, "synthetic")),
    )


def _binding() -> EvaluatorBinding:
    return EvaluatorBinding(
        name="synthetic",
        initialize_worker=worker_fixture.initialize,
        initializer_arguments=(0.25,),
        evaluate_cell=worker_fixture.evaluate,
        execution_routes=("synthetic",),
        summarize_tile=worker_fixture.summarize,
    )


def _execution() -> ProcessExecutionSpec:
    return ProcessExecutionSpec(
        process_width=2,
        chunksize=1,
        maximum_cells_per_pool=8,
    )


def test_create_resume_and_interrupted_retry_are_deterministic(tmp_path: Path) -> None:
    definition = _definition()
    complete_path = tmp_path / "complete.h5"
    created = run_scalar_field(
        complete_path,
        definition,
        _binding(),
        execution=_execution(),
        mode="create",
        progress_callback=(create_progress := []).append,
    )

    assert created.validation.accepted
    assert created.evaluated_cells == 15
    assert created.pool_count == 2
    assert created.recycling_events == 1
    assert created.all_workers_stopped
    assert created.validation.status_counts == {
        "not_yet_computed": 0,
        "completed_valid": 13,
        "completed_invalid": 1,
        "execution_error": 1,
    }
    assert create_progress[0].completed_work_units == 0
    assert create_progress[0].completed_cells == 0
    assert create_progress[-1].completed_work_units == 6
    assert create_progress[-1].completed_cells == 15
    assert [update.evaluated_work_units for update in create_progress] == list(
        range(7)
    )

    no_work = run_scalar_field(
        complete_path,
        definition,
        _binding(),
        execution=_execution(),
        mode="resume",
        progress_callback=(no_work_progress := []).append,
    )
    assert no_work.evaluated_cells == 0
    assert no_work.preexisting_completed_cells == 15
    assert no_work.pool_count == 0
    assert len(no_work_progress) == 1
    assert no_work_progress[0].completed_work_units == 6
    assert no_work_progress[0].evaluated_cells == 0

    resumed_path = tmp_path / "resumed.h5"
    shutil.copy2(complete_path, resumed_path)
    with h5py.File(resumed_path, "r+") as output:
        final_index = len(output["tiles/state"]) - 1
        output["tiles/state"][final_index] = np.uint8(TileState.WRITING)
        output["tiles/checksum"][final_index] = b""
        output.flush()
    resumed = run_scalar_field(
        resumed_path,
        definition,
        _binding(),
        execution=_execution(),
        mode="resume",
        progress_callback=(resume_progress := []).append,
    )
    complete = read_authoritative_field(complete_path)
    retried = read_authoritative_field(resumed_path)

    assert resumed.evaluated_cells == 1
    assert resumed.preexisting_completed_cells == 14
    assert resumed.validation.accepted
    assert resume_progress[0].completed_work_units == 5
    assert resume_progress[0].completed_cells == 14
    assert resume_progress[0].evaluated_cells == 0
    assert resume_progress[-1].completed_work_units == 6
    assert resume_progress[-1].completed_cells == 15
    assert resume_progress[-1].evaluated_cells == 1
    assert np.array_equal(complete.values, retried.values, equal_nan=True)
    assert np.array_equal(complete.status, retried.status)
    assert np.array_equal(complete.execution_route, retried.execution_route)


def test_file_modes_are_explicit_and_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "field.h5"
    with pytest.raises(FileNotFoundError):
        run_scalar_field(
            path,
            _definition(),
            _binding(),
            execution=_execution(),
            mode="resume",
        )
    run_scalar_field(
        path,
        _definition(),
        _binding(),
        execution=_execution(),
        mode="create",
    )
    with pytest.raises(FileExistsError):
        run_scalar_field(
            path,
            _definition(),
            _binding(),
            execution=_execution(),
            mode="create",
        )


def test_programming_error_propagates_and_does_not_complete_tile(
    tmp_path: Path,
) -> None:
    definition = _definition()
    path = tmp_path / "programming_error.h5"
    binding = EvaluatorBinding(
        name="synthetic",
        initialize_worker=worker_fixture.initialize,
        initializer_arguments=(0.25,),
        evaluate_cell=worker_fixture.raise_programming_error,
        execution_routes=("synthetic",),
    )

    with pytest.raises(ValueError, match="controlled programming error"):
        run_scalar_field(
            path,
            definition,
            binding,
            execution=_execution(),
            mode="create",
        )

    resume = discover_resume_state(path)
    assert not resume.completed_tile_indices
    assert resume.not_started_tile_indices == tuple(range(6))
