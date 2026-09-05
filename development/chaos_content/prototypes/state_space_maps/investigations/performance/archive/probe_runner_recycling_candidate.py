"""Validate 1024- versus 2048-cell recycling through the promoted field runner."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import tempfile
from collections import Counter
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from time import perf_counter
from typing import Mapping, Sequence
from unittest.mock import patch

import h5py
import numpy as np

from development.chaos_content.prototypes.state_space_maps.src.generation import (
    ProcessExecutionSpec,
    TileShape,
    discover_resume_state,
    plan_tiles,
    read_authoritative_field,
    tasks_for_work_unit,
    validate_dataset,
)
from development.chaos_content.prototypes.state_space_maps.src.generation import (
    runner as runner_module,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.field_adapter import (
    lyapunov_evaluator_binding,
    periodic_lyapunov_field_definition,
    validate_lyapunov_oracle_spots,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.hybrid import (
    HYBRID_FALLBACK_EVALUATOR,
    HYBRID_FAST_EVALUATOR,
)
from development.chaos_content.prototypes.state_space_maps.src.lyapunov.reference import (
    RenormalizedTangentSpec,
)

from .probe_worker_lifetime import (
    _current_rss_bytes,
    _jsonable,
    _rss_summary,
    _sha256,
)


PROBE_DIRECTORY = Path(__file__).resolve().parent
PROTOTYPE_DIRECTORY = PROBE_DIRECTORY.parents[2]
EVIDENCE_DIRECTORY = PROBE_DIRECTORY.parent / "evidence" / "lifecycle"
OPERATIONAL_OUTPUT_DIRECTORY = PROTOTYPE_DIRECTORY / "outputs" / "finite_time_field"
DEFAULT_OPERATIONAL_FIELD = (
    OPERATIONAL_OUTPUT_DIRECTORY / "finite_time_field_1024.h5"
)
DEFAULT_DESIGN_OUTPUT = EVIDENCE_DIRECTORY / "runner_recycling_candidate_design.json"
DEFAULT_OUTPUT = EVIDENCE_DIRECTORY / "runner_recycling_candidate_64.json"

SAMPLES_PER_AXIS = 64
OPERATIONAL_SAMPLES_PER_AXIS = 1024
OPERATIONAL_INDEX_STRIDE = OPERATIONAL_SAMPLES_PER_AXIS // SAMPLES_PER_AXIS
INTERRUPT_AFTER_TILES = 32
CELLS_PER_TILE = 64
CELLS_PER_QUARTER = 1024
POLICY_A = "accepted_1024"
POLICY_B = "candidate_2048"
PREREGISTERED_ORDER = (
    (1, (POLICY_A, POLICY_B)),
    (2, (POLICY_B, POLICY_A)),
    (3, (POLICY_A, POLICY_B)),
)


class PlannedInterruption(RuntimeError):
    """Stop after an already persisted tile to exercise normal resume."""


def _text(value: object) -> str:
    return value.decode("utf-8") if isinstance(value, bytes) else str(value)


def _canonical_digest(value: object) -> str:
    encoded = json.dumps(
        _jsonable(value),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _array_digest(*arrays: np.ndarray) -> str:
    digest = hashlib.sha256()
    for array in arrays:
        contiguous = np.ascontiguousarray(array)
        dtype = contiguous.dtype.str.encode("ascii")
        digest.update(len(dtype).to_bytes(2, "little"))
        digest.update(dtype)
        digest.update(np.asarray(contiguous.shape, dtype="<i8").tobytes())
        digest.update(contiguous.tobytes())
    return digest.hexdigest()


def _tree_digest(directory: Path) -> dict[str, object]:
    files = tuple(sorted(directory.rglob("*.py")))
    digest = hashlib.sha256()
    for path in files:
        relative = path.relative_to(PROTOTYPE_DIRECTORY).as_posix().encode("utf-8")
        payload = path.read_bytes()
        digest.update(len(relative).to_bytes(4, "little"))
        digest.update(relative)
        digest.update(len(payload).to_bytes(8, "little"))
        digest.update(payload)
    return {"python_file_count": len(files), "sha256": digest.hexdigest()}


def _promoted_tree_digests() -> dict[str, object]:
    return {
        name: _tree_digest(PROTOTYPE_DIRECTORY / name)
        for name in ("src", "runners", "tests")
    }


def _operational_artifact_hashes() -> dict[str, str]:
    return {
        path.relative_to(PROTOTYPE_DIRECTORY).as_posix(): _sha256(path)
        for path in sorted(OPERATIONAL_OUTPUT_DIRECTORY.rglob("*"))
        if path.is_file()
    }


def _task_plan_digest(definition: object) -> str:
    work_units = plan_tiles(
        definition.field_shape,
        TileShape(*definition.nominal_tile_shape),
    )
    payload = [
        (
            task.linear_index,
            task.theta2_index,
            task.theta1_index,
            task.theta2_coordinate,
            task.theta1_coordinate,
        )
        for work_unit in work_units
        for task in tasks_for_work_unit(
            work_unit,
            definition.theta1_axis,
            definition.theta2_axis,
        )
    ]
    return _canonical_digest(payload)


def _expected_route_evidence(
    operational_field: Path,
    definition: object,
) -> dict[str, object]:
    if OPERATIONAL_SAMPLES_PER_AXIS % SAMPLES_PER_AXIS:
        raise AssertionError("The bounded grid must be an exact operational subsample.")
    with h5py.File(operational_field, "r") as source:
        metadata = json.loads(_text(source.attrs["definition_json"]))
        routes = np.asarray(
            source["field/execution_route"][
                ::OPERATIONAL_INDEX_STRIDE,
                ::OPERATIONAL_INDEX_STRIDE,
            ],
            dtype=np.uint8,
        )
        statuses = np.asarray(
            source["field/status"][
                ::OPERATIONAL_INDEX_STRIDE,
                ::OPERATIONAL_INDEX_STRIDE,
            ],
            dtype=np.uint8,
        )
        values = np.asarray(
            source["field/values"][
                ::OPERATIONAL_INDEX_STRIDE,
                ::OPERATIONAL_INDEX_STRIDE,
            ],
            dtype="<f8",
        )
        theta1 = np.asarray(
            source["axes/theta1"][::OPERATIONAL_INDEX_STRIDE],
            dtype="<f8",
        )
        theta2 = np.asarray(
            source["axes/theta2"][::OPERATIONAL_INDEX_STRIDE],
            dtype="<f8",
        )

    expected_theta1 = np.asarray(definition.theta1_axis, dtype="<f8")
    expected_theta2 = np.asarray(definition.theta2_axis, dtype="<f8")
    if not np.array_equal(theta1, expected_theta1) or not np.array_equal(
        theta2, expected_theta2
    ):
        raise AssertionError("The 64-grid coordinates are not an exact 1024 subsample.")
    if (
        routes.shape != definition.field_shape
        or statuses.shape != definition.field_shape
    ):
        raise AssertionError("The persisted operational subsample has the wrong shape.")

    route_vocabulary = {
        int(code): label
        for code, label in metadata["execution_route_vocabulary"].items()
    }
    status_vocabulary = {
        int(code): label for code, label in metadata["status_vocabulary"].items()
    }
    fallback_code = next(
        code
        for code, label in route_vocabulary.items()
        if label == HYBRID_FALLBACK_EVALUATOR
    )
    tile_fallback_counts = tuple(
        int(
            np.count_nonzero(
                routes[row : row + 8, column : column + 8] == fallback_code
            )
        )
        for row in range(0, SAMPLES_PER_AXIS, 8)
        for column in range(0, SAMPLES_PER_AXIS, 8)
    )
    route_counts = {
        route_vocabulary[int(code)]: int(count)
        for code, count in zip(*np.unique(routes, return_counts=True), strict=True)
    }
    status_counts = {
        status_vocabulary[int(code)]: int(count)
        for code, count in zip(*np.unique(statuses, return_counts=True), strict=True)
    }
    return {
        "operational_field_path": str(operational_field),
        "operational_field_sha256": _sha256(operational_field),
        "selection_rule": (
            "Use the complete 64 x 64 full-periodic grid; coordinate (i, j) "
            "is persisted 1024-grid coordinate (16*i, 16*j). Selection uses "
            "no tile timing or rendered structure."
        ),
        "index_stride": OPERATIONAL_INDEX_STRIDE,
        "axes_match_exactly": True,
        "route_counts": route_counts,
        "fallback_fraction": route_counts.get(HYBRID_FALLBACK_EVALUATOR, 0)
        / routes.size,
        "status_counts": status_counts,
        "fallback_cells_per_row_major_tile": list(tile_fallback_counts),
        "fallback_cells_per_1024_cell_quarter": [
            sum(tile_fallback_counts[start : start + 16])
            for start in range(0, len(tile_fallback_counts), 16)
        ],
        "fallback_containing_tiles": sum(value > 0 for value in tile_fallback_counts),
        "fast_only_tiles": sum(value == 0 for value in tile_fallback_counts),
        "reference_payload_sha256": _array_digest(
            theta1,
            theta2,
            values,
            statuses,
            routes,
        ),
    }


def _policies() -> dict[str, ProcessExecutionSpec]:
    accepted = runner_module.accepted_process_execution_spec()
    candidate = replace(accepted, maximum_cells_per_pool=2048)
    accepted_values = asdict(accepted)
    candidate_values = asdict(candidate)
    differences = {
        key
        for key in accepted_values
        if accepted_values[key] != candidate_values[key]
    }
    if differences != {"maximum_cells_per_pool"}:
        raise AssertionError("The policies must differ only in pool lifetime.")
    return {POLICY_A: accepted, POLICY_B: candidate}


def build_design(operational_field: Path) -> dict[str, object]:
    specification = RenormalizedTangentSpec()
    definition = periodic_lyapunov_field_definition(
        SAMPLES_PER_AXIS,
        specification,
    )
    work_units = plan_tiles(
        definition.field_shape,
        TileShape(*definition.nominal_tile_shape),
    )
    policies = _policies()
    expected = _expected_route_evidence(operational_field, definition)
    return {
        "question": (
            "runner-level accepted 1024-cell recycling versus candidate "
            "2048-cell recycling"
        ),
        "workload": {
            "samples_per_axis": SAMPLES_PER_AXIS,
            "shape_theta2_theta1": list(definition.field_shape),
            "cell_count": int(np.prod(definition.field_shape)),
            "tile_shape_theta2_theta1": list(definition.nominal_tile_shape),
            "tile_count": len(work_units),
            "cells_per_full_tile": CELLS_PER_TILE,
            "task_plan_sha256": _task_plan_digest(definition),
            "operational_1024_subsample": expected,
            "fraction_of_512_squared_field": SAMPLES_PER_AXIS**2 / 512**2,
            "fraction_of_1024_squared_field": SAMPLES_PER_AXIS**2 / 1024**2,
        },
        "scientific_contract": {
            "observable": dict(definition.observable_provenance),
            "physical_parameters": dict(definition.physical_parameters),
            "numerical_parameters": dict(definition.numerical_parameters),
            "evaluator": dict(definition.evaluator_provenance),
            "periodic_interval": definition.periodic_interval,
            "orientation": "values[theta2_index, theta1_index]",
        },
        "policies": {
            POLICY_A: {
                "execution": asdict(policies[POLICY_A]),
                "expected_pool_lifetimes_per_uninterrupted_field": 4,
                "expected_worker_process_lifetimes_per_uninterrupted_field": 16,
            },
            POLICY_B: {
                "execution": asdict(policies[POLICY_B]),
                "expected_pool_lifetimes_per_uninterrupted_field": 2,
                "expected_worker_process_lifetimes_per_uninterrupted_field": 8,
            },
        },
        "only_policy_difference": "maximum_cells_per_pool: 1024 versus 2048",
        "uninterrupted_repetitions_per_policy": 3,
        "preregistered_order": [
            {"repetition": repetition, "order": list(order)}
            for repetition, order in PREREGISTERED_ORDER
        ],
        "resume_validation": {
            "policies": [POLICY_A, POLICY_B],
            "interrupt_after_completed_tiles": INTERRUPT_AFTER_TILES,
            "preexisting_completed_cells_on_resume": (
                INTERRUPT_AFTER_TILES * CELLS_PER_TILE
            ),
            "rule": (
                "Raise from the coordinator progress callback only after tile 31 "
                "has completed its authoritative write; then resume the same path "
                "with the same policy."
            ),
        },
        "measurement": {
            "primary_wall": (
                "outer run_scalar_field wall minus separately timed ps RSS observations"
            ),
            "phases": [
                "setup_and_warmup",
                "tile_evaluation",
                "coordinator_persistence",
                "shutdown",
            ],
            "rss_checkpoints_pool_wide_cells": [1024, 2048],
            "oracle": "established 3 x 3 mechanically selected oracle spots",
        },
        "temporary_artifacts": (
            "created below investigations/performance and deleted after evidence "
            "extraction; operational outputs are read-only"
        ),
        "promoted_source_modified": False,
    }


class PoolObserver:
    """Observe pool RSS around runner boundaries without changing runner code."""

    def __init__(self) -> None:
        self._original_open = runner_module._open_pool
        self._original_close = runner_module._close_pool
        self.records: list[dict[str, object]] = []
        self.active: dict[str, object] | None = None
        self.last_progress: object | None = None
        self.rss_observation_seconds = 0.0

    def _sample(
        self,
        process_ids: Sequence[int],
        ready: Mapping[str, int],
    ) -> dict[str, object]:
        started = perf_counter()
        snapshot = _current_rss_bytes(process_ids)
        self.rss_observation_seconds += perf_counter() - started
        if snapshot["errors_by_pid"]:
            raise RuntimeError(f"Current RSS unavailable: {snapshot['errors_by_pid']}")
        return _rss_summary(snapshot, dict(ready))

    def open_pool(
        self,
        binding: object,
        execution: ProcessExecutionSpec,
    ) -> tuple[object, tuple[object, ...], float]:
        executor, identities, setup_seconds = self._original_open(binding, execution)
        process_ids = tuple(identity.process_id for identity in identities)
        try:
            started = perf_counter()
            ready_raw = _current_rss_bytes(process_ids)
            self.rss_observation_seconds += perf_counter() - started
            if ready_raw["errors_by_pid"]:
                raise RuntimeError(
                    f"Current RSS unavailable: {ready_raw['errors_by_pid']}"
                )
            ready_by_pid = {
                str(key): int(value)
                for key, value in ready_raw["rss_bytes_by_pid"].items()
            }
        except BaseException:
            self._original_close(executor, identities)
            raise
        start_evaluated = (
            int(self.last_progress.evaluated_cells)
            if self.last_progress is not None
            else 0
        )
        record: dict[str, object] = {
            "pool_ordinal": len(self.records) + 1,
            "execution": asdict(execution),
            "setup_seconds": setup_seconds,
            "worker_identities": [_jsonable(identity) for identity in identities],
            "process_ids": list(process_ids),
            "invocation_evaluated_cells_at_open": start_evaluated,
            "ready_rss": _rss_summary(ready_raw, ready_by_pid),
            "checkpoints": [],
        }
        record["ready_rss_by_pid"] = ready_by_pid
        self.records.append(record)
        self.active = record
        return executor, identities, setup_seconds

    def observe_progress(self, progress: object) -> None:
        self.last_progress = progress
        if (
            self.active is None
            or progress.evaluated_cells == 0
            or progress.evaluated_cells % CELLS_PER_QUARTER
        ):
            return
        start_evaluated = int(self.active["invocation_evaluated_cells_at_open"])
        checkpoint = {
            "artifact_completed_cells": int(progress.completed_cells),
            "invocation_evaluated_cells": int(progress.evaluated_cells),
            "pool_completed_cells": int(progress.evaluated_cells) - start_evaluated,
            "rss": self._sample(
                self.active["process_ids"],
                self.active["ready_rss_by_pid"],
            ),
        }
        self.active["checkpoints"].append(checkpoint)

    def close_pool(
        self,
        executor: object,
        identities: Sequence[object],
    ) -> tuple[float, bool]:
        record = self.active
        sample_error = None
        if record is not None:
            try:
                record["rss_before_shutdown"] = self._sample(
                    record["process_ids"],
                    record["ready_rss_by_pid"],
                )
            except BaseException as error:  # close first, then fail the probe
                sample_error = error
                record["rss_before_shutdown_error"] = (
                    f"{type(error).__name__}: {error}"
                )
        shutdown_seconds, all_workers_stopped = self._original_close(
            executor,
            identities,
        )
        if record is not None:
            record["shutdown_seconds"] = shutdown_seconds
            record["all_workers_stopped"] = all_workers_stopped
            record.pop("ready_rss_by_pid", None)
        self.active = None
        if sample_error is not None:
            raise sample_error
        return shutdown_seconds, all_workers_stopped


def _clean_tile_diagnostics(
    diagnostics: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    clean: list[dict[str, object]] = []
    for item in diagnostics:
        retained = dict(item)
        retained.pop("summed_evaluator_seconds", None)
        retained.pop("worker_peak_rss_bytes", None)
        clean.append(retained)
    return clean


def _artifact_record(path: Path) -> tuple[dict[str, object], dict[str, object]]:
    storage_validation = validate_dataset(path)
    snapshot = read_authoritative_field(path)
    with h5py.File(path, "r") as source:
        metadata = json.loads(_text(source.attrs["definition_json"]))
        tile_bounds = np.asarray(source["tiles/bounds"], dtype="<i8")
        tile_identities = np.asarray(source["tiles/identity"])
        tile_states = np.asarray(source["tiles/state"], dtype=np.uint8)
        tile_checksums = tuple(_text(value) for value in source["tiles/checksum"][:])
        tile_attempts = np.asarray(source["tiles/attempt"], dtype="<u4")
        evaluation_seconds = np.asarray(
            source["tiles/evaluation_seconds"],
            dtype="<f8",
        )
        diagnostics = tuple(
            json.loads(_text(value)) for value in source["tiles/diagnostics_json"][:]
        )
        provenance = tuple(
            json.loads(_text(value)) for value in source["tiles/provenance_json"][:]
        )
        exceptional = tuple(
            json.loads(_text(value))
            for value in source["tiles/exceptional_cells_json"][:]
        )
        static_integrity = _text(source.attrs["static_integrity_sha256"])

    route_vocabulary = {
        int(code): label
        for code, label in metadata["execution_route_vocabulary"].items()
    }
    status_vocabulary = {
        int(code): label for code, label in metadata["status_vocabulary"].items()
    }
    route_counts = {
        route_vocabulary[int(code)]: int(count)
        for code, count in zip(
            *np.unique(snapshot.execution_route, return_counts=True),
            strict=True,
        )
    }
    status_counts = {
        status_vocabulary[int(code)]: int(count)
        for code, count in zip(
            *np.unique(snapshot.status, return_counts=True),
            strict=True,
        )
    }
    tile_records = [
        {
            "tile_index": index,
            "bounds_theta2_theta1": list(map(int, tile_bounds[index])),
            "evaluation_seconds": float(evaluation_seconds[index]),
            "summed_evaluator_seconds": float(
                diagnostics[index]["summed_evaluator_seconds"]
            ),
            "route_counts": diagnostics[index]["route_counts"],
            "status_counts": diagnostics[index]["status_counts"],
            "worker_peak_rss_bytes": diagnostics[index]["worker_peak_rss_bytes"],
            "execution_policy": provenance[index]["execution_policy"],
            "attempt": int(tile_attempts[index]),
        }
        for index in range(len(tile_bounds))
    ]
    quarter_records: list[dict[str, object]] = []
    for quarter, start in enumerate(range(0, len(tile_records), 16), start=1):
        group = tile_records[start : start + 16]
        route_counter: Counter[str] = Counter()
        status_counter: Counter[str] = Counter()
        for tile in group:
            route_counter.update(tile["route_counts"])
            status_counter.update(tile["status_counts"])
        tile_wall = sum(float(tile["evaluation_seconds"]) for tile in group)
        evaluator_wall = sum(
            float(tile["summed_evaluator_seconds"]) for tile in group
        )
        quarter_records.append(
            {
                "quarter": quarter,
                "tile_indices": [start, start + 15],
                "cell_count": CELLS_PER_QUARTER,
                "tile_evaluation_seconds": tile_wall,
                "cells_per_tile_evaluation_second": CELLS_PER_QUARTER / tile_wall,
                "summed_evaluator_seconds": evaluator_wall,
                "evaluator_occupancy_proxy": evaluator_wall / (4 * tile_wall),
                "route_counts": dict(sorted(route_counter.items())),
                "status_counts": dict(sorted(status_counter.items())),
            }
        )

    payload = {
        "theta1": np.asarray(snapshot.theta1_axis, dtype="<f8"),
        "theta2": np.asarray(snapshot.theta2_axis, dtype="<f8"),
        "values": np.asarray(snapshot.values, dtype="<f8"),
        "status": np.asarray(snapshot.status, dtype=np.uint8),
        "route": np.asarray(snapshot.execution_route, dtype=np.uint8),
        "clean_diagnostics": _clean_tile_diagnostics(diagnostics),
        "exceptional": exceptional,
        "metadata": metadata,
        "tile_bounds": tile_bounds,
        "tile_identities": tile_identities,
    }
    record = {
        "temporary_path": str(path),
        "artifact_sha256": _sha256(path),
        "artifact_bytes": path.stat().st_size,
        "storage_validation": _jsonable(storage_validation),
        "resume_state": _jsonable(snapshot.resume_state),
        "static_integrity_sha256": static_integrity,
        "authoritative_payload_sha256": _array_digest(
            payload["theta1"],
            payload["theta2"],
            payload["values"],
            payload["status"],
            payload["route"],
        ),
        "scientific_tile_diagnostics_sha256": _canonical_digest(
            payload["clean_diagnostics"]
        ),
        "exceptional_cells_sha256": _canonical_digest(exceptional),
        "tile_plan_sha256": _array_digest(tile_bounds, tile_identities),
        "route_counts": route_counts,
        "status_counts": status_counts,
        "tile_state_counts": {
            str(int(state)): int(count)
            for state, count in zip(
                *np.unique(tile_states, return_counts=True),
                strict=True,
            )
        },
        "tile_attempt_counts": {
            str(int(attempt)): int(count)
            for attempt, count in zip(
                *np.unique(tile_attempts, return_counts=True),
                strict=True,
            )
        },
        "all_tile_checksums_present": all(len(value) == 64 for value in tile_checksums),
        "execution_limits_in_tile_provenance": sorted(
            {
                int(item["execution_policy"]["maximum_cells_per_pool"])
                for item in provenance
            }
        ),
        "tile_records": tile_records,
        "quarters": quarter_records,
    }
    return record, payload


def _payload_comparison(
    reference: Mapping[str, object],
    candidate: Mapping[str, object],
) -> dict[str, object]:
    checks = {
        "theta1_axes_exact": np.array_equal(reference["theta1"], candidate["theta1"]),
        "theta2_axes_exact": np.array_equal(reference["theta2"], candidate["theta2"]),
        "values_exact": np.array_equal(
            reference["values"], candidate["values"], equal_nan=True
        ),
        "statuses_exact": np.array_equal(reference["status"], candidate["status"]),
        "routes_exact": np.array_equal(reference["route"], candidate["route"]),
        "scientific_tile_diagnostics_exact": (
            reference["clean_diagnostics"] == candidate["clean_diagnostics"]
        ),
        "exceptional_cells_exact": reference["exceptional"] == candidate["exceptional"],
        "definition_metadata_exact": reference["metadata"] == candidate["metadata"],
        "tile_bounds_exact": np.array_equal(
            reference["tile_bounds"], candidate["tile_bounds"]
        ),
        "tile_identities_exact": np.array_equal(
            reference["tile_identities"], candidate["tile_identities"]
        ),
    }
    return {"accepted": all(checks.values()), "checks": checks}


def _reference_comparison(
    payload: Mapping[str, object],
    operational_field: Path,
) -> dict[str, object]:
    with h5py.File(operational_field, "r") as source:
        values = np.asarray(
            source["field/values"][
                ::OPERATIONAL_INDEX_STRIDE,
                ::OPERATIONAL_INDEX_STRIDE,
            ],
            dtype="<f8",
        )
        statuses = np.asarray(
            source["field/status"][
                ::OPERATIONAL_INDEX_STRIDE,
                ::OPERATIONAL_INDEX_STRIDE,
            ],
            dtype=np.uint8,
        )
        routes = np.asarray(
            source["field/execution_route"][
                ::OPERATIONAL_INDEX_STRIDE,
                ::OPERATIONAL_INDEX_STRIDE,
            ],
            dtype=np.uint8,
        )
    checks = {
        "values_exact": np.array_equal(payload["values"], values, equal_nan=True),
        "statuses_exact": np.array_equal(payload["status"], statuses),
        "routes_exact": np.array_equal(payload["route"], routes),
    }
    return {"accepted": all(checks.values()), "checks": checks}


def _run_once(
    path: Path,
    execution: ProcessExecutionSpec,
    *,
    mode: str,
    interrupt_after_tiles: int | None = None,
) -> dict[str, object]:
    specification = RenormalizedTangentSpec()
    definition = periodic_lyapunov_field_definition(
        SAMPLES_PER_AXIS,
        specification,
    )
    observer = PoolObserver()

    def progress(update: object) -> None:
        observer.observe_progress(update)
        if (
            interrupt_after_tiles is not None
            and update.evaluated_work_units == interrupt_after_tiles
        ):
            raise PlannedInterruption(
                f"Planned stop after {interrupt_after_tiles} completed tiles."
            )

    summary = None
    interruption = None
    outer_started = perf_counter()
    with (
        patch.object(runner_module, "_open_pool", observer.open_pool),
        patch.object(runner_module, "_close_pool", observer.close_pool),
    ):
        try:
            summary = runner_module.run_scalar_field(
                path,
                definition,
                lyapunov_evaluator_binding(specification),
                execution=execution,
                mode=mode,
                progress_callback=progress,
            )
        except PlannedInterruption as error:
            interruption = str(error)
    outer_wall = perf_counter() - outer_started
    result = {
        "mode": mode,
        "planned_interruption": interruption,
        "outer_wall_seconds": outer_wall,
        "rss_observation_seconds": observer.rss_observation_seconds,
        "adjusted_outer_wall_seconds": outer_wall - observer.rss_observation_seconds,
        "summary": _jsonable(summary),
        "pools": observer.records,
        "all_observed_workers_stopped": all(
            bool(pool.get("all_workers_stopped")) for pool in observer.records
        ),
    }
    if interrupt_after_tiles is None and summary is None:
        raise AssertionError("An uninterrupted field run returned no summary.")
    if interrupt_after_tiles is not None and interruption is None:
        raise AssertionError("The planned interruption did not occur.")
    return result


def _summary(values: Sequence[float]) -> dict[str, float]:
    return {
        "mean": mean(values),
        "median": median(values),
        "minimum": min(values),
        "maximum": max(values),
    }


def _comparison(runs: Sequence[Mapping[str, object]]) -> dict[str, object]:
    by_repetition: dict[int, dict[str, Mapping[str, object]]] = {}
    for run in runs:
        by_repetition.setdefault(int(run["repetition"]), {})[
            str(run["policy"])
        ] = run
    pairs: list[dict[str, object]] = []
    for repetition in sorted(by_repetition):
        accepted = by_repetition[repetition][POLICY_A]
        candidate = by_repetition[repetition][POLICY_B]
        accepted_summary = accepted["run"]["summary"]
        candidate_summary = candidate["run"]["summary"]
        wall_saving = (
            float(accepted["run"]["adjusted_outer_wall_seconds"])
            - float(candidate["run"]["adjusted_outer_wall_seconds"])
        )
        lifecycle_saving = (
            float(accepted_summary["setup_seconds"])
            + float(accepted_summary["shutdown_seconds"])
            - float(candidate_summary["setup_seconds"])
            - float(candidate_summary["shutdown_seconds"])
        )
        evaluation_penalty = (
            float(candidate_summary["evaluation_seconds"])
            - float(accepted_summary["evaluation_seconds"])
        )
        persistence_penalty = (
            float(candidate_summary["persistence_seconds"])
            - float(accepted_summary["persistence_seconds"])
        )
        pairs.append(
            {
                "repetition": repetition,
                "accepted_adjusted_outer_wall_seconds": accepted["run"][
                    "adjusted_outer_wall_seconds"
                ],
                "candidate_adjusted_outer_wall_seconds": candidate["run"][
                    "adjusted_outer_wall_seconds"
                ],
                "candidate_wall_saving_seconds": wall_saving,
                "candidate_wall_saving_fraction_of_accepted": wall_saving
                / float(accepted["run"]["adjusted_outer_wall_seconds"]),
                "candidate_lifecycle_saving_seconds": lifecycle_saving,
                "candidate_evaluation_penalty_seconds": evaluation_penalty,
                "candidate_persistence_penalty_seconds": persistence_penalty,
                "accepted_evaluation_cells_per_second": SAMPLES_PER_AXIS**2
                / float(accepted_summary["evaluation_seconds"]),
                "candidate_evaluation_cells_per_second": SAMPLES_PER_AXIS**2
                / float(candidate_summary["evaluation_seconds"]),
            }
        )
    return {
        "pairs": pairs,
        "candidate_wall_saving_seconds": _summary(
            [float(pair["candidate_wall_saving_seconds"]) for pair in pairs]
        ),
        "candidate_wall_saving_fraction_of_accepted": _summary(
            [
                float(pair["candidate_wall_saving_fraction_of_accepted"])
                for pair in pairs
            ]
        ),
        "candidate_lifecycle_saving_seconds": _summary(
            [float(pair["candidate_lifecycle_saving_seconds"]) for pair in pairs]
        ),
        "candidate_evaluation_penalty_seconds": _summary(
            [float(pair["candidate_evaluation_penalty_seconds"]) for pair in pairs]
        ),
        "accepted_aggregate_evaluation_cells_per_second": (
            3 * SAMPLES_PER_AXIS**2
            / sum(
                float(run["run"]["summary"]["evaluation_seconds"])
                for run in runs
                if run["policy"] == POLICY_A
            )
        ),
        "candidate_aggregate_evaluation_cells_per_second": (
            3 * SAMPLES_PER_AXIS**2
            / sum(
                float(run["run"]["summary"]["evaluation_seconds"])
                for run in runs
                if run["policy"] == POLICY_B
            )
        ),
    }


def _oracle_record(path: Path) -> dict[str, object]:
    started = perf_counter()
    result = validate_lyapunov_oracle_spots(path)
    return {
        "wall_seconds": perf_counter() - started,
        "result": _jsonable(result),
    }


def _write_json(path: Path, payload: object) -> None:
    if path.exists():
        raise FileExistsError(f"Refusing to replace investigation evidence: {path}")
    path.write_text(
        json.dumps(_jsonable(payload), indent=2, sort_keys=True, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--operational-field",
        type=Path,
        default=DEFAULT_OPERATIONAL_FIELD,
        help="Read-only completed 1024 HDF5 evidence used to fix the 64-grid mix.",
    )
    parser.add_argument(
        "--design-output",
        type=Path,
        default=DEFAULT_DESIGN_OUTPUT,
        help="Investigation-local preregistration JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Investigation-local machine-readable result JSON.",
    )
    parser.add_argument(
        "--design-only",
        action="store_true",
        help="Write the fixed workload/order record without scientific evaluation.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    design = build_design(arguments.operational_field)
    if arguments.design_only:
        payload = {
            "probe": "runner_recycling_candidate_design",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "python": platform.python_version(),
            "design": design,
            "design_sha256": _canonical_digest(design),
            "timing_results_known": False,
        }
        _write_json(arguments.design_output, payload)
        print(json.dumps(payload, indent=2, sort_keys=True), flush=True)
        return 0

    if arguments.output.exists():
        raise FileExistsError(
            f"Refusing to replace investigation evidence: {arguments.output}"
        )
    preregistration = json.loads(arguments.design_output.read_text(encoding="utf-8"))
    if preregistration["design"] != design:
        raise RuntimeError("The current design differs from the preregistered design.")
    if preregistration["design_sha256"] != _canonical_digest(design):
        raise RuntimeError("The preregistered design digest is invalid.")
    if preregistration["timing_results_known"] is not False:
        raise RuntimeError("The design record was not created before timing.")

    operational_hashes_before = _operational_artifact_hashes()
    promoted_hashes_before = _promoted_tree_digests()
    policies = _policies()
    uninterrupted_runs: list[dict[str, object]] = []
    payloads: dict[tuple[int, str], dict[str, object]] = {}
    sequence = 0

    with tempfile.TemporaryDirectory(
        prefix="runner_recycling_candidate_",
        dir=PROBE_DIRECTORY,
    ) as temporary_name:
        temporary_directory = Path(temporary_name)
        for repetition, order in PREREGISTERED_ORDER:
            for order_position, policy_name in enumerate(order, start=1):
                sequence += 1
                path = temporary_directory / (
                    f"create_rep{repetition}_{policy_name}.h5"
                )
                run = _run_once(
                    path,
                    policies[policy_name],
                    mode="create",
                )
                artifact, field_payload = _artifact_record(path)
                oracle = _oracle_record(path)
                reference = _reference_comparison(
                    field_payload,
                    arguments.operational_field,
                )
                record = {
                    "execution_sequence_number": sequence,
                    "repetition": repetition,
                    "order_position_within_repetition": order_position,
                    "policy": policy_name,
                    "run": run,
                    "artifact": artifact,
                    "oracle": oracle,
                    "operational_subsample_comparison": reference,
                }
                uninterrupted_runs.append(record)
                payloads[(repetition, policy_name)] = field_payload
                print(
                    f"{sequence}/6 rep {repetition} {policy_name}: "
                    f"{run['adjusted_outer_wall_seconds']:.3f} s adjusted wall | "
                    f"{run['summary']['evaluation_seconds']:.3f} s evaluation | "
                    f"{artifact['route_counts']}",
                    flush=True,
                )

        paired_scientific_comparisons = []
        for repetition in range(1, 4):
            comparison = _payload_comparison(
                payloads[(repetition, POLICY_A)],
                payloads[(repetition, POLICY_B)],
            )
            paired_scientific_comparisons.append(
                {"repetition": repetition, **comparison}
            )

        resume_runs: list[dict[str, object]] = []
        for policy_name in (POLICY_A, POLICY_B):
            path = temporary_directory / f"resume_{policy_name}.h5"
            partial = _run_once(
                path,
                policies[policy_name],
                mode="create",
                interrupt_after_tiles=INTERRUPT_AFTER_TILES,
            )
            partial_state = discover_resume_state(path)
            with h5py.File(path, "r") as source:
                partial_attempts = np.asarray(source["tiles/attempt"], dtype=np.uint32)
                partial_states = np.asarray(source["tiles/state"], dtype=np.uint8)
            resume = _run_once(
                path,
                policies[policy_name],
                mode="resume",
            )
            artifact, field_payload = _artifact_record(path)
            oracle = _oracle_record(path)
            uninterrupted_reference = payloads[(1, policy_name)]
            comparison = _payload_comparison(
                uninterrupted_reference,
                field_payload,
            )
            operational_reference = _reference_comparison(
                field_payload,
                arguments.operational_field,
            )
            record = {
                "policy": policy_name,
                "partial_create": partial,
                "partial_state": _jsonable(partial_state),
                "partial_tile_attempt_counts": {
                    str(int(value)): int(count)
                    for value, count in zip(
                        *np.unique(partial_attempts, return_counts=True),
                        strict=True,
                    )
                },
                "partial_tile_state_counts": {
                    str(int(value)): int(count)
                    for value, count in zip(
                        *np.unique(partial_states, return_counts=True),
                        strict=True,
                    )
                },
                "resume": resume,
                "artifact": artifact,
                "oracle": oracle,
                "uninterrupted_scientific_comparison": comparison,
                "operational_subsample_comparison": operational_reference,
            }
            resume_runs.append(record)
            print(
                f"resume {policy_name}: skipped "
                f"{resume['summary']['preexisting_completed_cells']} cells | "
                f"final equality {comparison['accepted']} | "
                f"oracle {oracle['result']['accepted']}",
                flush=True,
            )

        temporary_entries_before_cleanup = sorted(
            path.relative_to(temporary_directory).as_posix()
            for path in temporary_directory.rglob("*")
            if path.is_file()
        )

    operational_hashes_after = _operational_artifact_hashes()
    promoted_hashes_after = _promoted_tree_digests()
    comparison = _comparison(uninterrupted_runs)

    all_pool_records = [
        pool
        for record in uninterrupted_runs
        for pool in record["run"]["pools"]
    ] + [
        pool
        for record in resume_runs
        for phase in (record["partial_create"], record["resume"])
        for pool in phase["pools"]
    ]
    validation = {
        "preregistered_design_matched": True,
        "uninterrupted_run_count": len(uninterrupted_runs),
        "uninterrupted_policy_counts": dict(
            Counter(str(record["policy"]) for record in uninterrupted_runs)
        ),
        "uninterrupted_measured_field_cells": sum(
            int(record["run"]["summary"]["evaluated_cells"])
            for record in uninterrupted_runs
        ),
        "resume_sequence_count": len(resume_runs),
        "resume_sequence_measured_field_cells": sum(
            INTERRUPT_AFTER_TILES * CELLS_PER_TILE
            + int(record["resume"]["summary"]["evaluated_cells"])
            for record in resume_runs
        ),
        "initializer_warmup_evaluations": 4 * len(all_pool_records),
        "oracle_spot_count": sum(
            len(record["oracle"]["result"]["comparisons"])
            for record in (*uninterrupted_runs, *resume_runs)
        ),
        "all_worker_pools_stopped": all(
            bool(pool["all_workers_stopped"]) for pool in all_pool_records
        ),
        "all_storage_validations_accepted": all(
            bool(record["artifact"]["storage_validation"]["accepted"])
            for record in (*uninterrupted_runs, *resume_runs)
        ),
        "all_oracles_accepted": all(
            bool(record["oracle"]["result"]["accepted"])
            for record in (*uninterrupted_runs, *resume_runs)
        ),
        "all_operational_subsample_comparisons_exact": all(
            bool(record["operational_subsample_comparison"]["accepted"])
            for record in (*uninterrupted_runs, *resume_runs)
        ),
        "all_paired_policy_science_exact": all(
            bool(record["accepted"])
            for record in paired_scientific_comparisons
        ),
        "all_resumed_science_exact": all(
            bool(record["uninterrupted_scientific_comparison"]["accepted"])
            for record in resume_runs
        ),
        "all_resume_skipping_exact": all(
            record["resume"]["summary"]["completed_tiles_before"]
            == INTERRUPT_AFTER_TILES
            and record["resume"]["summary"]["preexisting_completed_cells"]
            == INTERRUPT_AFTER_TILES * CELLS_PER_TILE
            and record["resume"]["summary"]["evaluated_cells"]
            == SAMPLES_PER_AXIS**2 - INTERRUPT_AFTER_TILES * CELLS_PER_TILE
            for record in resume_runs
        ),
        "all_final_tile_attempts_one": all(
            record["artifact"]["tile_attempt_counts"] == {"1": 64}
            for record in (*uninterrupted_runs, *resume_runs)
        ),
        "operational_artifacts_byte_identical": (
            operational_hashes_before == operational_hashes_after
        ),
        "promoted_python_trees_byte_identical": (
            promoted_hashes_before == promoted_hashes_after
        ),
        "temporary_artifact_count": len(temporary_entries_before_cleanup),
        "temporary_artifacts_removed": True,
    }
    payload = {
        "probe": "runner_recycling_candidate_1024_vs_2048",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "preregistration": {
            "path": str(arguments.design_output),
            "sha256": _sha256(arguments.design_output),
            "design_sha256": preregistration["design_sha256"],
            "created_at_utc": preregistration["created_at_utc"],
            "timing_results_known_when_written": False,
        },
        "design": design,
        "uninterrupted_runs": uninterrupted_runs,
        "paired_scientific_comparisons": paired_scientific_comparisons,
        "comparison": comparison,
        "resume_runs": resume_runs,
        "protected_evidence": {
            "operational_hashes_before": operational_hashes_before,
            "operational_hashes_after": operational_hashes_after,
            "promoted_tree_digests_before": promoted_hashes_before,
            "promoted_tree_digests_after": promoted_hashes_after,
        },
        "temporary_artifacts": {
            "sandbox_parent": str(PROBE_DIRECTORY),
            "files_created_and_removed": temporary_entries_before_cleanup,
        },
        "validation": validation,
        "promoted_implementation_modified": False,
    }
    _write_json(arguments.output, payload)
    print(f"Probe evidence written: {arguments.output}", flush=True)
    required = (
        validation["preregistered_design_matched"],
        validation["uninterrupted_run_count"] == 6,
        validation["uninterrupted_policy_counts"]
        == {POLICY_A: 3, POLICY_B: 3},
        validation["uninterrupted_measured_field_cells"] == 24_576,
        validation["resume_sequence_measured_field_cells"] == 8_192,
        validation["all_worker_pools_stopped"],
        validation["all_storage_validations_accepted"],
        validation["all_oracles_accepted"],
        validation["all_operational_subsample_comparisons_exact"],
        validation["all_paired_policy_science_exact"],
        validation["all_resumed_science_exact"],
        validation["all_resume_skipping_exact"],
        validation["all_final_tile_attempts_one"],
        validation["operational_artifacts_byte_identical"],
        validation["promoted_python_trees_byte_identical"],
    )
    return 0 if all(required) else 1


if __name__ == "__main__":
    raise SystemExit(main())
