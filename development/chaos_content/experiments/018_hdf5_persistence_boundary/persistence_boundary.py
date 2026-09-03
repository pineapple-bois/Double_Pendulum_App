"""Experiment 018: validate an HDF5 scalar-field persistence boundary."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, replace
from pathlib import Path

import h5py
import numpy as np


EXPERIMENT_ROOT = Path(__file__).resolve().parent
EXPERIMENT_017_ROOT = EXPERIMENT_ROOT.parent / "017_rectangular_work_unit_boundary"
REPOSITORY_ROOT = EXPERIMENT_ROOT.parents[3]
for _path in (EXPERIMENT_ROOT, EXPERIMENT_017_ROOT, REPOSITORY_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import rectangular_work_unit_boundary as work_units

from development.chaos_content.prototypes.state_space_maps.src.lyapunov.hybrid import (
    HYBRID_FALLBACK_EVALUATOR,
    HYBRID_FAST_ERROR_EVALUATOR,
    HYBRID_FAST_EVALUATOR,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.reference import (
    RenormalizedTangentSpec,
)

from hdf5_field_store import (
    ORIENTATION,
    STATUS_VOCABULARY,
    CellState,
    CompletedTile,
    DuplicateTileConflict,
    FieldDefinition,
    SimulatedInterruption,
    create_dataset,
    discover_resume_state,
    inspect_dataset,
    read_authoritative_field,
    validate_dataset,
    write_completed_tile,
)


EXPERIMENT_NAME = "hdf5_persistence_boundary"
OUTPUT_DIRECTORY = (
    EXPERIMENT_ROOT.parents[1] / "outputs" / EXPERIMENT_NAME
)
DATASET_PATH = OUTPUT_DIRECTORY / "reference_scalar_field.h5"
CORRUPTED_DATASET_PATH = OUTPUT_DIRECTORY / "corrupted_scalar_field.h5"
EVIDENCE_PATH = OUTPUT_DIRECTORY / "summary.json"
NOMINAL_TILE_SHAPE = work_units.TileShape(8, 8)
ROUTE_VOCABULARY = (
    (0, "not_yet_computed"),
    (1, HYBRID_FAST_EVALUATOR),
    (2, HYBRID_FALLBACK_EVALUATOR),
    (3, HYBRID_FAST_ERROR_EVALUATOR),
)


def experiment_field_definition() -> FieldDefinition:
    """Describe the accepted periodic field and first-consumer provenance."""

    context = work_units.periodic_coordinate_context()
    spec = RenormalizedTangentSpec()
    return FieldDefinition(
        theta1_axis=context.theta1_axis,
        theta2_axis=context.theta2_axis,
        coordinate_unit=context.coordinate_unit,
        periodic=context.periodic,
        periodic_interval="[-pi, pi)",
        nominal_tile_shape=(
            NOMINAL_TILE_SHAPE.theta2_cells,
            NOMINAL_TILE_SHAPE.theta1_cells,
        ),
        observable_provenance={
            "name": "one_vector_finite_time_tangent_stretching_rate",
            "symbol": "Lambda_T^(1)",
            "authoritative_meaning": "finite-time scalar observable",
            "fixture_values": "deterministic storage-only data; not dynamics",
        },
        physical_parameters=asdict(spec.parameters),
        numerical_parameters={
            "duration_seconds": spec.duration,
            "renormalization_interval_seconds": spec.renormalization_interval,
            "sampling_interval_seconds": spec.sampling_interval,
            "initial_tangent": list(spec.initial_tangent),
            "initial_angular_velocities_radians_per_second": [0.0, 0.0],
            "candidate_a_characteristic_length": spec.characteristic_length,
            "energy_drift_limit": spec.energy_drift_limit,
            "renormalization_norm_tolerance": spec.renormalization_norm_tolerance,
            "solver": asdict(spec.solver),
        },
        evaluator_provenance={
            "policy": "targeted_hybrid",
            "normal_route": HYBRID_FAST_EVALUATOR,
            "fallback_route": HYBRID_FALLBACK_EVALUATOR,
            "bounded_error_route": HYBRID_FAST_ERROR_EVALUATOR,
            "scientific_oracles": [
                "numpy_sympy_solve_ivp",
                "numba_rhs_jvp_solve_ivp",
            ],
        },
        software_provenance={
            "experiment": "018_hdf5_persistence_boundary",
            "python": platform.python_version(),
            "numpy": np.__version__,
            "h5py": h5py.__version__,
            "hdf5": h5py.version.hdf5_version,
            "platform": platform.platform(),
        },
        route_vocabulary=ROUTE_VOCABULARY,
    )


def accepted_tile_plan() -> tuple[work_units.TileWorkUnit, ...]:
    context = work_units.periodic_coordinate_context()
    return work_units.plan_tiles(context, NOMINAL_TILE_SHAPE)


def deterministic_completed_tile(
    tile_index: int,
    work_unit: work_units.TileWorkUnit,
    *,
    attempt: int = 1,
) -> CompletedTile:
    """Build compact deterministic payloads without evaluating dynamics."""

    bounds = work_unit.bounds
    values = np.empty(bounds.shape, dtype="<f8")
    status = np.full(bounds.shape, CellState.COMPLETED_VALID, dtype=np.uint8)
    route = np.full(bounds.shape, 1, dtype=np.uint8)
    exceptional: list[dict[str, object]] = []
    for local_theta2 in range(bounds.shape[0]):
        for local_theta1 in range(bounds.shape[1]):
            theta2_index, theta1_index = bounds.global_indices(
                local_theta2, local_theta1
            )
            values[local_theta2, local_theta1] = (
                1000.0 * theta2_index + theta1_index + 0.125
            )
            linear_index = theta2_index * work_unit.context.shape[1] + theta1_index
            if linear_index % 17 == 0:
                route[local_theta2, local_theta1] = 2

            if (theta2_index, theta1_index) == (2, 3):
                status[local_theta2, local_theta1] = CellState.COMPLETED_INVALID
                exceptional.append(
                    {
                        "theta2_index": theta2_index,
                        "theta1_index": theta1_index,
                        "state": "completed_invalid",
                        "issues": ["controlled storage fixture invalidity"],
                    }
                )
            elif (theta2_index, theta1_index) == (12, 19):
                status[local_theta2, local_theta1] = CellState.EXECUTION_ERROR
                route[local_theta2, local_theta1] = 3
                values[local_theta2, local_theta1] = np.nan
                exceptional.append(
                    {
                        "theta2_index": theta2_index,
                        "theta1_index": theta1_index,
                        "state": "execution_error",
                        "error_type": "ControlledStorageFixtureError",
                        "error_message": "No scalar value was produced.",
                    }
                )

    bounds_tuple = (
        bounds.theta2_start,
        bounds.theta2_stop,
        bounds.theta1_start,
        bounds.theta1_stop,
    )
    return CompletedTile(
        bounds=bounds_tuple,
        values=values,
        status=status,
        execution_route=route,
        attempt=attempt,
        evaluation_seconds=0.001 * (tile_index + 1),
        diagnostics={
            "completed_valid_cells": int(
                np.count_nonzero(status == CellState.COMPLETED_VALID)
            ),
            "completed_invalid_cells": int(
                np.count_nonzero(status == CellState.COMPLETED_INVALID)
            ),
            "execution_error_cells": int(
                np.count_nonzero(status == CellState.EXECUTION_ERROR)
            ),
            "maximum_energy_drift": 1.0e-10 * (tile_index + 1),
            "maximum_reset_norm_error": 1.0e-16 * (tile_index + 1),
        },
        provenance={
            "tile_index": tile_index,
            "global_bounds_theta2_theta1": list(bounds_tuple),
            "payload_kind": "deterministic_storage_fixture",
            "array_orientation": ORIENTATION,
        },
        exceptional_cells=tuple(exceptional),
    )


def _assembled_expected(
    payloads: tuple[CompletedTile, ...],
    shape: tuple[int, int],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    values = np.full(shape, np.nan, dtype="<f8")
    status = np.zeros(shape, dtype=np.uint8)
    route = np.zeros(shape, dtype=np.uint8)
    for payload in payloads:
        theta2_start, theta2_stop, theta1_start, theta1_stop = payload.bounds
        region = np.s_[theta2_start:theta2_stop, theta1_start:theta1_stop]
        values[region] = payload.values
        status[region] = payload.status
        route[region] = payload.execution_route
    return values, status, route


def _arrays_equal(left: np.ndarray, right: np.ndarray) -> bool:
    return bool(np.array_equal(left, right, equal_nan=True))


def run_experiment(output_directory: Path = OUTPUT_DIRECTORY) -> dict[str, object]:
    output_directory.mkdir(parents=True, exist_ok=True)
    dataset_path = output_directory / DATASET_PATH.name
    corrupted_path = output_directory / CORRUPTED_DATASET_PATH.name
    evidence_path = output_directory / EVIDENCE_PATH.name
    for generated_path in (dataset_path, corrupted_path, evidence_path):
        if generated_path.exists():
            generated_path.unlink()

    definition = experiment_field_definition()
    work_unit_plan = accepted_tile_plan()
    payloads = tuple(
        deterministic_completed_tile(index, work_unit)
        for index, work_unit in enumerate(work_unit_plan)
    )
    bounds = tuple(work_unit.bounds for work_unit in work_unit_plan)
    create_dataset(dataset_path, definition, bounds)

    fresh = inspect_dataset(dataset_path)
    first_write = write_completed_tile(dataset_path, 0, payloads[0])
    first_snapshot = read_authoritative_field(dataset_path)
    first_bounds = payloads[0].bounds
    first_region = np.s_[
        first_bounds[0]:first_bounds[1], first_bounds[2]:first_bounds[3]
    ]
    first_readback_exact = bool(
        _arrays_equal(first_snapshot.values[first_region], payloads[0].values)
        and np.array_equal(first_snapshot.status[first_region], payloads[0].status)
        and np.array_equal(
            first_snapshot.execution_route[first_region],
            payloads[0].execution_route,
        )
    )

    duplicate_identical = write_completed_tile(dataset_path, 0, payloads[0])
    conflicting_values = payloads[0].values.copy()
    conflicting_values[0, 0] += 1.0
    conflict_rejected = False
    try:
        write_completed_tile(
            dataset_path,
            0,
            replace(payloads[0], values=conflicting_values),
        )
    except DuplicateTileConflict:
        conflict_rejected = True

    interrupted = False
    try:
        write_completed_tile(
            dataset_path,
            1,
            payloads[1],
            interrupt_after="payload",
        )
    except SimulatedInterruption:
        interrupted = True
    interrupted_resume = discover_resume_state(dataset_path)
    interrupted_snapshot = read_authoritative_field(dataset_path)
    interrupted_bounds = payloads[1].bounds
    interrupted_region = np.s_[
        interrupted_bounds[0]:interrupted_bounds[1],
        interrupted_bounds[2]:interrupted_bounds[3],
    ]
    partial_payload_hidden = bool(
        np.all(np.isnan(interrupted_snapshot.values[interrupted_region]))
        and np.all(
            interrupted_snapshot.status[interrupted_region]
            == CellState.NOT_YET_COMPUTED
        )
        and np.all(interrupted_snapshot.execution_route[interrupted_region] == 0)
    )

    retry_payload = replace(payloads[1], attempt=2)
    retry_write = write_completed_tile(dataset_path, 1, retry_payload)
    after_retry = discover_resume_state(dataset_path)
    pending_before_completion = after_retry.pending_tile_indices
    skipped_completed_during_resume = tuple(
        index
        for index in range(len(payloads))
        if index not in pending_before_completion
    )
    for tile_index in pending_before_completion:
        write_completed_tile(dataset_path, tile_index, payloads[tile_index])

    validation = validate_dataset(dataset_path)
    snapshot = read_authoritative_field(dataset_path)
    expected_values, expected_status, expected_route = _assembled_expected(
        payloads,
        definition.field_shape,
    )
    full_readback_exact = bool(
        _arrays_equal(snapshot.values, expected_values)
        and np.array_equal(snapshot.status, expected_status)
        and np.array_equal(snapshot.execution_route, expected_route)
        and np.array_equal(snapshot.theta1_axis, definition.theta1_axis)
        and np.array_equal(snapshot.theta2_axis, definition.theta2_axis)
    )

    coordinate_checks = []
    for theta2_index, theta1_index in ((0, 0), (7, 8), (24, 32)):
        coordinate_checks.append(
            {
                "indices_theta2_theta1": [theta2_index, theta1_index],
                "theta1_radians": float(snapshot.theta1_axis[theta1_index]),
                "theta2_radians": float(snapshot.theta2_axis[theta2_index]),
                "value": float(snapshot.values[theta2_index, theta1_index]),
                "expected_value": 1000.0 * theta2_index + theta1_index + 0.125,
                "matches": bool(
                    snapshot.values[theta2_index, theta1_index]
                    == 1000.0 * theta2_index + theta1_index + 0.125
                ),
            }
        )

    independent_process = subprocess.run(
        [sys.executable, str(EXPERIMENT_ROOT / "hdf5_field_store.py"), str(dataset_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    independent_inspection = json.loads(independent_process.stdout)

    shutil.copy2(dataset_path, corrupted_path)
    with h5py.File(corrupted_path, "r+") as corrupted:
        corrupted["field/values"][0, 0] += 0.5
        corrupted.flush()
    corruption_validation = validate_dataset(corrupted_path)
    corruption_resume = discover_resume_state(corrupted_path)

    status_counts = {
        label: int(np.count_nonzero(snapshot.status == code))
        for code, label in STATUS_VOCABULARY.items()
    }
    route_counts = {
        label: int(np.count_nonzero(snapshot.execution_route == code))
        for code, label in ROUTE_VOCABULARY
    }
    accepted = bool(
        fresh["accepted"]
        and fresh["cell_state_counts"]["not_yet_computed"]
        == int(np.prod(definition.field_shape))
        and first_write == "completed"
        and first_readback_exact
        and duplicate_identical == "already_complete_identical"
        and conflict_rejected
        and interrupted
        and interrupted_resume.completed_tile_indices == (0,)
        and interrupted_resume.writing_tile_indices == (1,)
        and partial_payload_hidden
        and retry_write == "completed"
        and skipped_completed_during_resume == (0, 1)
        and validation.accepted
        and not validation.resume_state.pending_tile_indices
        and not validation.resume_state.corrupt_tile_indices
        and full_readback_exact
        and all(item["matches"] for item in coordinate_checks)
        and independent_inspection["accepted"]
        and independent_inspection["completed_tile_indices"]
        == list(range(len(payloads)))
        and not corruption_validation.accepted
        and corruption_resume.corrupt_tile_indices == (0,)
    )
    evidence = {
        "experiment": EXPERIMENT_NAME,
        "verdict": "ACCEPT" if accepted else "REJECT",
        "storage": {
            "technology": "HDF5",
            "library": "h5py",
            "dataset_path": str(dataset_path),
            "corrupted_dataset_path": str(corrupted_path),
            "dataset_bytes": dataset_path.stat().st_size,
            "corrupted_dataset_bytes": corrupted_path.stat().st_size,
            "chunk_shape_theta2_theta1": [
                NOMINAL_TILE_SHAPE.theta2_cells,
                NOMINAL_TILE_SHAPE.theta1_cells,
            ],
            "compression": "gzip level 4 + shuffle + Fletcher32",
            "custom_integrity": "SHA-256 static digest and per-completed-tile digest",
        },
        "field": {
            "shape_theta2_theta1": list(definition.field_shape),
            "resolution_theta1_theta2": list(definition.resolution),
            "orientation": ORIENTATION,
            "periodic_interval": definition.periodic_interval,
            "positive_pi_absent": bool(
                math_pi_absent(snapshot.theta1_axis)
                and math_pi_absent(snapshot.theta2_axis)
            ),
            "tile_count": len(payloads),
            "status_counts": status_counts,
            "route_counts": route_counts,
        },
        "creation_and_readback": {
            "fresh_state_counts": fresh["cell_state_counts"],
            "first_tile_readback_exact": first_readback_exact,
            "full_field_readback_exact": full_readback_exact,
            "axes_exact": bool(
                np.array_equal(snapshot.theta1_axis, definition.theta1_axis)
                and np.array_equal(snapshot.theta2_axis, definition.theta2_axis)
            ),
            "metadata_exact": snapshot.metadata == independent_inspection["metadata"],
            "coordinate_checks": coordinate_checks,
        },
        "completion_and_resume": {
            "interruption_stage": "after payload flush, before checksum/completion",
            "interruption_observed": interrupted,
            "partial_payload_hidden": partial_payload_hidden,
            "resume_completed_after_interruption": list(
                interrupted_resume.completed_tile_indices
            ),
            "resume_writing_after_interruption": list(
                interrupted_resume.writing_tile_indices
            ),
            "retry_result": retry_write,
            "completed_tiles_skipped_by_resume": list(
                skipped_completed_during_resume
            ),
            "final_completed_tiles": list(
                validation.resume_state.completed_tile_indices
            ),
            "final_pending_tiles": list(validation.resume_state.pending_tile_indices),
        },
        "duplicate_completion": {
            "identical_result": duplicate_identical,
            "conflicting_completion_rejected": conflict_rejected,
        },
        "integrity": {
            "uncorrupted_accepted": validation.accepted,
            "uncorrupted_issues": list(validation.issues),
            "corrupted_accepted": corruption_validation.accepted,
            "corruption_issues": list(corruption_validation.issues),
            "corrupt_tile_indices": list(corruption_resume.corrupt_tile_indices),
        },
        "independent_reopen": {
            "subprocess_accepted": independent_inspection["accepted"],
            "completed_tile_count": len(
                independent_inspection["completed_tile_indices"]
            ),
            "dynamics_modules_required": False,
        },
        "environment": experiment_field_definition().software_provenance,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    return evidence


def math_pi_absent(axis: np.ndarray) -> bool:
    return not bool(np.any(axis == np.pi))


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-directory", type=Path, default=OUTPUT_DIRECTORY)
    arguments = parser.parse_args()
    evidence = run_experiment(arguments.output_directory)
    print(
        json.dumps(
            {
                "verdict": evidence["verdict"],
                "dataset_path": evidence["storage"]["dataset_path"],
                "evidence_path": str(arguments.output_directory / EVIDENCE_PATH.name),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    _main()
