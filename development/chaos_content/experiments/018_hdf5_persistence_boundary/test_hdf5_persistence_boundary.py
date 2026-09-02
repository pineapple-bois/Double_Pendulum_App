from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path

import h5py
import numpy as np
import pytest

import persistence_boundary as experiment
from hdf5_field_store import (
    CellState,
    DuplicateTileConflict,
    SimulatedInterruption,
    create_dataset,
    discover_resume_state,
    read_authoritative_field,
    validate_dataset,
    write_completed_tile,
)


def _fixture(tmp_path: Path):
    definition = experiment.experiment_field_definition()
    plan = experiment.accepted_tile_plan()
    payloads = tuple(
        experiment.deterministic_completed_tile(index, work_unit)
        for index, work_unit in enumerate(plan)
    )
    path = tmp_path / "field.h5"
    create_dataset(path, definition, tuple(item.bounds for item in plan))
    return definition, payloads, path


def test_fresh_dataset_preserves_periodic_axes_orientation_and_unknown_state(
    tmp_path: Path,
) -> None:
    definition, _payloads, path = _fixture(tmp_path)

    snapshot = read_authoritative_field(path)

    assert snapshot.values.shape == (25, 33)
    assert definition.resolution == (33, 25)
    assert np.array_equal(snapshot.theta1_axis, definition.theta1_axis)
    assert np.array_equal(snapshot.theta2_axis, definition.theta2_axis)
    assert np.all(snapshot.theta1_axis < np.pi)
    assert np.all(snapshot.theta2_axis < np.pi)
    assert np.all(np.isnan(snapshot.values))
    assert np.all(snapshot.status == CellState.NOT_YET_COMPUTED)
    assert snapshot.metadata["orientation"] == "values[theta2_index, theta1_index]"
    assert snapshot.resume_state.not_started_tile_indices == tuple(range(20))


def test_completion_marker_is_last_and_incomplete_tile_can_be_retried(
    tmp_path: Path,
) -> None:
    _definition, payloads, path = _fixture(tmp_path)
    write_completed_tile(path, 0, payloads[0])

    with pytest.raises(SimulatedInterruption):
        write_completed_tile(path, 1, payloads[1], interrupt_after="payload")

    resume = discover_resume_state(path)
    snapshot = read_authoritative_field(path)
    bounds = payloads[1].bounds
    region = np.s_[bounds[0]:bounds[1], bounds[2]:bounds[3]]
    assert resume.completed_tile_indices == (0,)
    assert resume.writing_tile_indices == (1,)
    assert np.all(np.isnan(snapshot.values[region]))
    assert np.all(snapshot.status[region] == CellState.NOT_YET_COMPUTED)

    assert (
        write_completed_tile(path, 1, replace(payloads[1], attempt=2))
        == "completed"
    )
    assert discover_resume_state(path).completed_tile_indices == (0, 1)


def test_duplicate_conflict_and_completed_tile_corruption_fail_closed(
    tmp_path: Path,
) -> None:
    _definition, payloads, path = _fixture(tmp_path)
    assert write_completed_tile(path, 0, payloads[0]) == "completed"
    assert (
        write_completed_tile(path, 0, payloads[0])
        == "already_complete_identical"
    )

    conflicting_values = payloads[0].values.copy()
    conflicting_values[0, 0] += 1.0
    with pytest.raises(DuplicateTileConflict):
        write_completed_tile(
            path,
            0,
            replace(payloads[0], values=conflicting_values),
        )

    corrupted = tmp_path / "corrupted.h5"
    shutil.copy2(path, corrupted)
    with h5py.File(corrupted, "r+") as output:
        output["field/values"][0, 0] += 0.5
        output.flush()

    validation = validate_dataset(corrupted)
    assert not validation.accepted
    assert validation.resume_state.corrupt_tile_indices == (0,)
    assert "checksum mismatch" in validation.issues[0]
    corrupted_snapshot = read_authoritative_field(corrupted)
    assert np.all(np.isnan(corrupted_snapshot.values[:8, :8]))
    assert np.all(
        corrupted_snapshot.status[:8, :8] == CellState.NOT_YET_COMPUTED
    )


def test_completed_tile_retains_compact_status_route_and_sparse_detail(
    tmp_path: Path,
) -> None:
    _definition, payloads, path = _fixture(tmp_path)
    for index, payload in enumerate(payloads):
        write_completed_tile(path, index, payload)

    snapshot = read_authoritative_field(path)
    assert validate_dataset(path).accepted
    assert snapshot.status[2, 3] == CellState.COMPLETED_INVALID
    assert snapshot.status[12, 19] == CellState.EXECUTION_ERROR
    assert np.isnan(snapshot.values[12, 19])
    assert snapshot.execution_route[12, 19] == 3
    assert snapshot.execution_route[0, 0] == 2
    assert snapshot.values[7, 8] == 7008.125
    with h5py.File(path, "r") as source:
        exceptional = source["tiles/exceptional_cells_json"][0]
        if isinstance(exceptional, bytes):
            exceptional = exceptional.decode("utf-8")
        assert "controlled storage fixture invalidity" in exceptional


def test_full_experiment_meets_acceptance_boundary(tmp_path: Path) -> None:
    evidence = experiment.run_experiment(tmp_path / "evidence")

    assert evidence["verdict"] == "ACCEPT"
    assert evidence["field"]["status_counts"] == {
        "not_yet_computed": 0,
        "completed_valid": 823,
        "completed_invalid": 1,
        "execution_error": 1,
    }
    assert evidence["completion_and_resume"]["partial_payload_hidden"]
    assert evidence["duplicate_completion"]["conflicting_completion_rejected"]
    assert not evidence["integrity"]["corrupted_accepted"]
    assert evidence["independent_reopen"]["dynamics_modules_required"] is False
