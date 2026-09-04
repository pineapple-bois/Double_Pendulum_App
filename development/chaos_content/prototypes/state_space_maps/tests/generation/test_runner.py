from __future__ import annotations

import json
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
    accepted_process_execution_spec,
    discover_resume_state,
    read_authoritative_field,
    run_scalar_field,
)
from development.chaos_content.prototypes.state_space_maps.src.generation import (
    runner as runner_module,
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


def _default_boundary_definition() -> FieldDefinition:
    return FieldDefinition(
        theta1_axis=tuple(float(index) for index in range(264)),
        theta2_axis=tuple(float(index) for index in range(8)),
        coordinate_unit="radians",
        periodic=False,
        periodic_interval=None,
        nominal_tile_shape=(8, 8),
        observable_provenance={"name": "synthetic_default_policy_boundary"},
        physical_parameters={},
        numerical_parameters={"offset": 0.25},
        evaluator_provenance={"binding": "synthetic"},
        software_provenance={"revision": "test"},
        route_vocabulary=((0, "not_yet_computed"), (1, "synthetic")),
    )


def _install_inline_pool_probe(monkeypatch) -> list[tuple[int, tuple[int, ...]]]:
    """Keep the policy-boundary regression fast while observing tile dispatch."""

    batches: list[tuple[int, tuple[int, ...]]] = []
    opened_pools = 0

    class InlineExecutor:
        def __init__(self, binding: EvaluatorBinding, pool_index: int) -> None:
            self.binding = binding
            self.pool_index = pool_index

        def map(self, function, tasks, *, chunksize):
            assert function is runner_module._evaluate_bound_cell
            assert chunksize == 1
            materialized = tuple(tasks)
            batches.append(
                (
                    self.pool_index,
                    tuple(task.linear_index for task in materialized),
                )
            )
            return tuple(
                runner_module.CellOutcome(
                    task=task,
                    evaluation=self.binding.evaluate_cell(task),
                    worker_pid=self.pool_index,
                    worker_peak_rss_bytes=0,
                )
                for task in materialized
            )

    def open_pool(binding, execution):
        nonlocal opened_pools
        opened_pools += 1
        if binding.initialize_worker is not None:
            binding.initialize_worker(*binding.initializer_arguments)
        return InlineExecutor(binding, opened_pools), (), 0.0

    def close_pool(executor, identities):
        assert isinstance(executor, InlineExecutor)
        assert identities == ()
        return 0.0, True

    monkeypatch.setattr(runner_module, "_open_pool", open_pool)
    monkeypatch.setattr(runner_module, "_close_pool", close_pool)
    return batches


def _tile_provenance(path: Path) -> list[dict[str, object]]:
    with h5py.File(path, "r") as source:
        return [
            json.loads(value)
            for value in source["tiles/provenance_json"]
        ]


def _mark_final_tile_incomplete(path: Path) -> None:
    with h5py.File(path, "r+") as output:
        final_index = len(output["tiles/state"]) - 1
        output["tiles/state"][final_index] = np.uint8(TileState.WRITING)
        output["tiles/checksum"][final_index] = b""
        output.flush()


def test_default_policy_recycles_pool_wide_at_a_tile_boundary(
    tmp_path: Path,
    monkeypatch,
) -> None:
    execution = accepted_process_execution_spec()
    assert execution == ProcessExecutionSpec()
    assert execution.maximum_cells_per_pool == 2048

    batches = _install_inline_pool_probe(monkeypatch)
    definition = _default_boundary_definition()
    complete_path = tmp_path / "default_policy_complete.h5"
    created = run_scalar_field(
        complete_path,
        definition,
        _binding(),
        mode="create",
    )

    assert created.validation.accepted
    assert created.evaluated_cells == 2112
    assert created.pool_count == 2
    assert created.recycling_events == 1
    assert created.all_workers_stopped
    assert len(batches) == 33
    assert all(len(linear_indices) == 64 for _, linear_indices in batches)
    assert [pool_index for pool_index, _ in batches] == [1] * 32 + [2]
    assert sum(len(indices) for pool, indices in batches if pool == 1) == 2048
    assert {
        provenance["execution_policy"]["maximum_cells_per_pool"]
        for provenance in _tile_provenance(complete_path)
    } == {2048}

    resumed_path = tmp_path / "default_policy_resumed.h5"
    shutil.copy2(complete_path, resumed_path)
    _mark_final_tile_incomplete(resumed_path)
    resumed = run_scalar_field(
        resumed_path,
        definition,
        _binding(),
        mode="resume",
    )
    complete = read_authoritative_field(complete_path)
    retried = read_authoritative_field(resumed_path)

    assert resumed.validation.accepted
    assert resumed.preexisting_completed_cells == 2048
    assert resumed.evaluated_cells == 64
    assert resumed.pool_count == 1
    assert resumed.recycling_events == 0
    assert np.array_equal(complete.values, retried.values, equal_nan=True)
    assert np.array_equal(complete.status, retried.status)
    assert np.array_equal(complete.execution_route, retried.execution_route)
    assert {
        provenance["execution_policy"]["maximum_cells_per_pool"]
        for provenance in _tile_provenance(resumed_path)
    } == {2048}


def test_cross_policy_resume_preserves_explicit_per_tile_provenance(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _install_inline_pool_probe(monkeypatch)
    definition = _definition()
    path = tmp_path / "old_policy_incomplete.h5"
    old_execution = ProcessExecutionSpec(maximum_cells_per_pool=1024)
    created = run_scalar_field(
        path,
        definition,
        _binding(),
        execution=old_execution,
        mode="create",
    )
    assert created.validation.accepted
    assert {
        provenance["execution_policy"]["maximum_cells_per_pool"]
        for provenance in _tile_provenance(path)
    } == {1024}

    _mark_final_tile_incomplete(path)
    resumed = run_scalar_field(
        path,
        definition,
        _binding(),
        mode="resume",
    )
    provenance = _tile_provenance(path)

    assert resumed.validation.accepted
    assert resumed.preexisting_completed_cells == 14
    assert resumed.evaluated_cells == 1
    assert {
        item["execution_policy"]["maximum_cells_per_pool"]
        for item in provenance[:-1]
    } == {1024}
    assert provenance[-1]["execution_policy"]["maximum_cells_per_pool"] == 2048


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
