"""Authoritative, dynamics-independent HDF5 scalar-field persistence."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Mapping, Sequence

import h5py
import numpy as np


SCHEMA_NAME = "double_pendulum_scalar_field"
SCHEMA_VERSION = 1
ORIENTATION = "values[theta2_index, theta1_index]"
STATUS_VOCABULARY = {
    0: "not_yet_computed",
    1: "completed_valid",
    2: "completed_invalid",
    3: "execution_error",
}


class CellState(IntEnum):
    NOT_YET_COMPUTED = 0
    COMPLETED_VALID = 1
    COMPLETED_INVALID = 2
    EXECUTION_ERROR = 3


class TileState(IntEnum):
    NOT_STARTED = 0
    WRITING = 1
    COMPLETE = 2


class PersistenceError(RuntimeError):
    """Base class for bounded persistence failures."""


class IntegrityError(PersistenceError):
    """Stored content does not match its declared integrity evidence."""


class DuplicateTileConflict(PersistenceError):
    """A completed tile was offered different content."""


@dataclass(frozen=True)
class FieldDefinition:
    theta1_axis: tuple[float, ...]
    theta2_axis: tuple[float, ...]
    coordinate_unit: str
    periodic: bool
    periodic_interval: str | None
    nominal_tile_shape: tuple[int, int]
    observable_provenance: Mapping[str, object]
    physical_parameters: Mapping[str, object]
    numerical_parameters: Mapping[str, object]
    evaluator_provenance: Mapping[str, object]
    software_provenance: Mapping[str, object]
    route_vocabulary: tuple[tuple[int, str], ...]
    scalar_dtype: str = "<f8"

    def __post_init__(self) -> None:
        for name, axis in (
            ("theta1_axis", self.theta1_axis),
            ("theta2_axis", self.theta2_axis),
        ):
            values = np.asarray(axis, dtype=float)
            if (
                values.ndim != 1
                or len(values) == 0
                or not np.all(np.isfinite(values))
                or (len(values) > 1 and np.any(np.diff(values) <= 0.0))
            ):
                raise ValueError(f"{name} must be finite and strictly increasing.")
        if not self.coordinate_unit:
            raise ValueError("coordinate_unit is required.")
        if self.periodic and self.periodic_interval != "[-pi, pi)":
            raise ValueError("Periodic angular fields must declare [-pi, pi).")
        if self.periodic:
            for axis in (self.theta1_axis, self.theta2_axis):
                values = np.asarray(axis, dtype=float)
                if np.any(values < -math.pi) or np.any(values >= math.pi):
                    raise ValueError("Periodic axes must remain inside [-pi, pi).")
        if len(self.nominal_tile_shape) != 2 or any(
            value <= 0 for value in self.nominal_tile_shape
        ):
            raise ValueError("nominal_tile_shape must contain two positive sizes.")
        if np.dtype(self.scalar_dtype) != np.dtype("<f8"):
            raise ValueError("The promoted scalar-field schema supports float64 values.")
        route_codes = [code for code, _label in self.route_vocabulary]
        route_labels = [label for _code, label in self.route_vocabulary]
        if (
            0 not in route_codes
            or len(route_codes) != len(set(route_codes))
            or len(route_labels) != len(set(route_labels))
            or any(not 0 <= code <= 255 for code in route_codes)
            or any(not label for label in route_labels)
        ):
            raise ValueError("route_vocabulary must be unique uint8 codes including zero.")

    @property
    def field_shape(self) -> tuple[int, int]:
        return (len(self.theta2_axis), len(self.theta1_axis))

    @property
    def resolution(self) -> tuple[int, int]:
        return (len(self.theta1_axis), len(self.theta2_axis))


@dataclass(frozen=True)
class CompletedTile:
    bounds: tuple[int, int, int, int]
    values: np.ndarray
    status: np.ndarray
    execution_route: np.ndarray
    attempt: int
    evaluation_seconds: float
    diagnostics: Mapping[str, object]
    provenance: Mapping[str, object]
    exceptional_cells: tuple[Mapping[str, object], ...] = ()


@dataclass(frozen=True)
class ResumeState:
    completed_tile_indices: tuple[int, ...]
    writing_tile_indices: tuple[int, ...]
    not_started_tile_indices: tuple[int, ...]
    corrupt_tile_indices: tuple[int, ...]

    @property
    def pending_tile_indices(self) -> tuple[int, ...]:
        return tuple(sorted((*self.writing_tile_indices, *self.not_started_tile_indices)))


@dataclass(frozen=True)
class FieldSnapshot:
    theta1_axis: np.ndarray
    theta2_axis: np.ndarray
    values: np.ndarray
    status: np.ndarray
    execution_route: np.ndarray
    resume_state: ResumeState
    metadata: dict[str, object]


@dataclass(frozen=True)
class DatasetValidation:
    accepted: bool
    issues: tuple[str, ...]
    resume_state: ResumeState


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _decode_string(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def _definition_metadata(definition: FieldDefinition) -> dict[str, object]:
    return {
        "schema_name": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "authoritative_artifact": "numerical_scalar_field",
        "orientation": ORIENTATION,
        "coordinate_unit": definition.coordinate_unit,
        "periodic": definition.periodic,
        "periodic_interval": definition.periodic_interval,
        "resolution_theta1_theta2": list(definition.resolution),
        "field_shape_theta2_theta1": list(definition.field_shape),
        "nominal_tile_shape_theta2_theta1": list(definition.nominal_tile_shape),
        "scalar_dtype": np.dtype(definition.scalar_dtype).str,
        "status_dtype": np.dtype("u1").str,
        "execution_route_dtype": np.dtype("u1").str,
        "status_vocabulary": STATUS_VOCABULARY,
        "execution_route_vocabulary": dict(definition.route_vocabulary),
        "observable_provenance": definition.observable_provenance,
        "physical_parameters": definition.physical_parameters,
        "numerical_parameters": definition.numerical_parameters,
        "evaluator_provenance": definition.evaluator_provenance,
        "software_provenance": definition.software_provenance,
    }


def _normalize_bounds(
    bounds: object,
    expected_shape: tuple[int, int],
) -> tuple[int, int, int, int]:
    if isinstance(bounds, tuple) and len(bounds) == 4:
        normalized = tuple(int(value) for value in bounds)
    else:
        normalized = (
            int(getattr(bounds, "theta2_start")),
            int(getattr(bounds, "theta2_stop")),
            int(getattr(bounds, "theta1_start")),
            int(getattr(bounds, "theta1_stop")),
        )
        global_shape = tuple(int(value) for value in getattr(bounds, "global_shape"))
        if global_shape != expected_shape:
            raise ValueError("Tile bounds use a different global field shape.")
    theta2_start, theta2_stop, theta1_start, theta1_stop = normalized
    if not (
        0 <= theta2_start < theta2_stop <= expected_shape[0]
        and 0 <= theta1_start < theta1_stop <= expected_shape[1]
    ):
        raise ValueError("Tile bounds must be nonempty, half-open, and in range.")
    return normalized


def _validate_tile_plan(
    field_shape: tuple[int, int],
    bounds: Sequence[tuple[int, int, int, int]],
) -> None:
    coverage = np.zeros(field_shape, dtype=np.uint16)
    for theta2_start, theta2_stop, theta1_start, theta1_stop in bounds:
        coverage[theta2_start:theta2_stop, theta1_start:theta1_stop] += 1
    if np.any(coverage != 1):
        raise ValueError("Tile plan must cover every global cell exactly once.")


def _static_integrity_digest(
    definition_json: str,
    theta1_axis: np.ndarray,
    theta2_axis: np.ndarray,
    bounds: np.ndarray,
) -> str:
    digest = hashlib.sha256()
    digest.update(definition_json.encode("utf-8"))
    digest.update(np.asarray(theta1_axis, dtype="<f8").tobytes())
    digest.update(np.asarray(theta2_axis, dtype="<f8").tobytes())
    digest.update(np.asarray(bounds, dtype="<i8").tobytes())
    return digest.hexdigest()


def _tile_identity(static_digest: str, bounds: Sequence[int]) -> str:
    digest = hashlib.sha256()
    digest.update(static_digest.encode("ascii"))
    digest.update(np.asarray(bounds, dtype="<i8").tobytes())
    return digest.hexdigest()


def create_dataset(
    path: Path,
    definition: FieldDefinition,
    tile_bounds: Sequence[object],
) -> Path:
    """Create a new authoritative field container with no completed cells."""

    normalized_bounds = tuple(
        _normalize_bounds(bounds, definition.field_shape) for bounds in tile_bounds
    )
    _validate_tile_plan(definition.field_shape, normalized_bounds)
    metadata = _definition_metadata(definition)
    definition_json = _canonical_json(metadata)
    theta1_axis = np.asarray(definition.theta1_axis, dtype="<f8")
    theta2_axis = np.asarray(definition.theta2_axis, dtype="<f8")
    bounds_array = np.asarray(normalized_bounds, dtype="<i8")
    static_digest = _static_integrity_digest(
        definition_json,
        theta1_axis,
        theta2_axis,
        bounds_array,
    )
    chunk_shape = (
        min(definition.nominal_tile_shape[0], definition.field_shape[0]),
        min(definition.nominal_tile_shape[1], definition.field_shape[1]),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    string_dtype = h5py.string_dtype(encoding="utf-8")
    with h5py.File(path, "x") as output:
        output.attrs["schema_name"] = SCHEMA_NAME
        output.attrs["schema_version"] = SCHEMA_VERSION
        output.attrs["definition_json"] = definition_json
        output.attrs["static_integrity_sha256"] = static_digest

        axes = output.create_group("axes")
        theta1 = axes.create_dataset("theta1", data=theta1_axis)
        theta2 = axes.create_dataset("theta2", data=theta2_axis)
        for dataset, name in ((theta1, "theta1"), (theta2, "theta2")):
            dataset.attrs["name"] = name
            dataset.attrs["unit"] = definition.coordinate_unit
            dataset.attrs["periodic"] = definition.periodic
            dataset.attrs["periodic_interval"] = definition.periodic_interval or ""

        field = output.create_group("field")
        common = {
            "shape": definition.field_shape,
            "chunks": chunk_shape,
            "compression": "gzip",
            "compression_opts": 4,
            "shuffle": True,
            "fletcher32": True,
        }
        values = field.create_dataset(
            "values",
            dtype=np.dtype(definition.scalar_dtype),
            fillvalue=np.nan,
            **common,
        )
        status = field.create_dataset(
            "status",
            dtype=np.uint8,
            fillvalue=np.uint8(CellState.NOT_YET_COMPUTED),
            **common,
        )
        route = field.create_dataset(
            "execution_route",
            dtype=np.uint8,
            fillvalue=np.uint8(0),
            **common,
        )
        values.attrs["authoritative"] = True
        values.attrs["orientation"] = ORIENTATION
        status.attrs["vocabulary_json"] = _canonical_json(STATUS_VOCABULARY)
        route.attrs["vocabulary_json"] = _canonical_json(
            dict(definition.route_vocabulary)
        )

        tiles = output.create_group("tiles")
        tile_count = len(normalized_bounds)
        tiles.create_dataset("bounds", data=bounds_array)
        tiles.create_dataset(
            "identity",
            data=np.asarray(
                [_tile_identity(static_digest, bounds) for bounds in normalized_bounds],
                dtype="S64",
            ),
        )
        tiles.create_dataset("state", shape=(tile_count,), dtype=np.uint8, fillvalue=0)
        tiles.create_dataset("checksum", shape=(tile_count,), dtype="S64", fillvalue=b"")
        tiles.create_dataset("attempt", shape=(tile_count,), dtype=np.uint32, fillvalue=0)
        tiles.create_dataset(
            "evaluation_seconds", shape=(tile_count,), dtype=np.float64, fillvalue=np.nan
        )
        tiles.create_dataset(
            "diagnostics_json", shape=(tile_count,), dtype=string_dtype
        )
        tiles.create_dataset(
            "provenance_json", shape=(tile_count,), dtype=string_dtype
        )
        tiles.create_dataset(
            "exceptional_cells_json", shape=(tile_count,), dtype=string_dtype
        )
        for name in ("diagnostics_json", "provenance_json", "exceptional_cells_json"):
            tiles[name][:] = ""
        output.flush()
    return path


def _tile_slice(bounds: Sequence[int]) -> tuple[slice, slice]:
    theta2_start, theta2_stop, theta1_start, theta1_stop = bounds
    return (
        slice(int(theta2_start), int(theta2_stop)),
        slice(int(theta1_start), int(theta1_stop)),
    )


def _tile_shape(bounds: Sequence[int]) -> tuple[int, int]:
    return (int(bounds[1] - bounds[0]), int(bounds[3] - bounds[2]))


def _validate_completed_tile(
    tile: CompletedTile,
    expected_bounds: tuple[int, int, int, int],
    route_codes: set[int],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, str, str, str]:
    if tile.bounds != expected_bounds:
        raise ValueError("Completed tile bounds do not match the planned work unit.")
    shape = _tile_shape(expected_bounds)
    values = np.asarray(tile.values, dtype="<f8")
    status = np.asarray(tile.status, dtype=np.uint8)
    route = np.asarray(tile.execution_route, dtype=np.uint8)
    if values.shape != shape or status.shape != shape or route.shape != shape:
        raise ValueError("Completed tile arrays must match the planned tile shape.")
    if np.any(status == CellState.NOT_YET_COMPUTED) or not set(
        int(value) for value in np.unique(status)
    ).issubset({1, 2, 3}):
        raise ValueError("A completed tile cannot contain unknown cell states.")
    if not set(int(value) for value in np.unique(route)).issubset(route_codes - {0}):
        raise ValueError("A completed tile contains an unknown execution route.")
    if np.any(~np.isfinite(values[status == CellState.COMPLETED_VALID])):
        raise ValueError("Completed-valid cells require finite scalar values.")
    if np.any(~np.isnan(values[status == CellState.EXECUTION_ERROR])):
        raise ValueError("Execution-error cells must retain NaN scalar values.")
    if tile.attempt <= 0:
        raise ValueError("Tile attempt must be positive.")
    if not math.isfinite(tile.evaluation_seconds) or tile.evaluation_seconds < 0.0:
        raise ValueError("Tile evaluation time must be finite and nonnegative.")
    diagnostics_json = _canonical_json(tile.diagnostics)
    provenance_json = _canonical_json(tile.provenance)
    exceptional_json = _canonical_json(list(tile.exceptional_cells))
    return values, status, route, diagnostics_json, provenance_json, exceptional_json


def _checksum_parts(
    identity: str,
    bounds: Sequence[int],
    values: np.ndarray,
    status: np.ndarray,
    route: np.ndarray,
    attempt: int,
    evaluation_seconds: float,
    diagnostics_json: str,
    provenance_json: str,
    exceptional_json: str,
) -> str:
    digest = hashlib.sha256()
    digest.update(identity.encode("ascii"))
    digest.update(np.asarray(bounds, dtype="<i8").tobytes())
    digest.update(np.asarray(values, dtype="<f8").tobytes())
    digest.update(np.asarray(status, dtype=np.uint8).tobytes())
    digest.update(np.asarray(route, dtype=np.uint8).tobytes())
    digest.update(np.asarray((attempt,), dtype="<u4").tobytes())
    digest.update(np.asarray((evaluation_seconds,), dtype="<f8").tobytes())
    for value in (diagnostics_json, provenance_json, exceptional_json):
        encoded = value.encode("utf-8")
        digest.update(np.asarray((len(encoded),), dtype="<u8").tobytes())
        digest.update(encoded)
    return digest.hexdigest()


def _checksum_from_file(source: h5py.File, tile_index: int) -> str:
    bounds = np.asarray(source["tiles/bounds"][tile_index], dtype=np.int64)
    region = _tile_slice(bounds)
    return _checksum_parts(
        _decode_string(source["tiles/identity"][tile_index]),
        bounds,
        np.asarray(source["field/values"][region]),
        np.asarray(source["field/status"][region]),
        np.asarray(source["field/execution_route"][region]),
        int(source["tiles/attempt"][tile_index]),
        float(source["tiles/evaluation_seconds"][tile_index]),
        _decode_string(source["tiles/diagnostics_json"][tile_index]),
        _decode_string(source["tiles/provenance_json"][tile_index]),
        _decode_string(source["tiles/exceptional_cells_json"][tile_index]),
    )


def _route_codes(source: h5py.File) -> set[int]:
    vocabulary = json.loads(
        _decode_string(source["field/execution_route"].attrs["vocabulary_json"])
    )
    return {int(code) for code in vocabulary}


def write_completed_tile(
    path: Path,
    tile_index: int,
    tile: CompletedTile,
) -> str:
    """Write payload, checksum, then the authoritative completion marker."""

    with h5py.File(path, "r+") as output:
        tile_count = len(output["tiles/state"])
        if not 0 <= tile_index < tile_count:
            raise IndexError("tile_index is outside the stored tile plan.")
        expected_bounds = tuple(
            int(value) for value in output["tiles/bounds"][tile_index]
        )
        (
            values,
            status,
            route,
            diagnostics_json,
            provenance_json,
            exceptional_json,
        ) = _validate_completed_tile(tile, expected_bounds, _route_codes(output))
        identity = _decode_string(output["tiles/identity"][tile_index])
        candidate_checksum = _checksum_parts(
            identity,
            expected_bounds,
            values,
            status,
            route,
            tile.attempt,
            tile.evaluation_seconds,
            diagnostics_json,
            provenance_json,
            exceptional_json,
        )
        state = TileState(int(output["tiles/state"][tile_index]))
        if state is TileState.COMPLETE:
            stored_checksum = _decode_string(output["tiles/checksum"][tile_index])
            actual_checksum = _checksum_from_file(output, tile_index)
            if stored_checksum != actual_checksum:
                raise IntegrityError("Completed tile content fails its stored checksum.")
            if candidate_checksum == stored_checksum:
                return "already_complete_identical"
            raise DuplicateTileConflict("Completed tile already has different content.")

        output["tiles/state"][tile_index] = np.uint8(TileState.WRITING)
        output["tiles/checksum"][tile_index] = b""
        output.flush()

        region = _tile_slice(expected_bounds)
        output["field/values"][region] = values
        output["field/status"][region] = status
        output["field/execution_route"][region] = route
        output["tiles/attempt"][tile_index] = np.uint32(tile.attempt)
        output["tiles/evaluation_seconds"][tile_index] = tile.evaluation_seconds
        output["tiles/diagnostics_json"][tile_index] = diagnostics_json
        output["tiles/provenance_json"][tile_index] = provenance_json
        output["tiles/exceptional_cells_json"][tile_index] = exceptional_json
        output.flush()

        stored_checksum = _checksum_from_file(output, tile_index)
        if stored_checksum != candidate_checksum:
            raise IntegrityError("Stored tile payload changed during write.")
        output["tiles/checksum"][tile_index] = stored_checksum.encode("ascii")
        output.flush()

        output["tiles/state"][tile_index] = np.uint8(TileState.COMPLETE)
        output.flush()
    return "completed"


def _static_issues(source: h5py.File) -> list[str]:
    issues: list[str] = []
    if _decode_string(source.attrs.get("schema_name", "")) != SCHEMA_NAME:
        issues.append("schema name mismatch")
    if int(source.attrs.get("schema_version", -1)) != SCHEMA_VERSION:
        issues.append("schema version mismatch")
    required = (
        "axes/theta1",
        "axes/theta2",
        "field/values",
        "field/status",
        "field/execution_route",
        "tiles/bounds",
        "tiles/identity",
        "tiles/state",
        "tiles/checksum",
        "tiles/attempt",
        "tiles/evaluation_seconds",
        "tiles/diagnostics_json",
        "tiles/provenance_json",
        "tiles/exceptional_cells_json",
    )
    for name in required:
        if name not in source:
            issues.append(f"missing dataset: {name}")
    if issues:
        return issues
    definition_json = _decode_string(source.attrs.get("definition_json", ""))
    bounds = np.asarray(source["tiles/bounds"])
    expected_static = _static_integrity_digest(
        definition_json,
        np.asarray(source["axes/theta1"]),
        np.asarray(source["axes/theta2"]),
        bounds,
    )
    if expected_static != _decode_string(
        source.attrs.get("static_integrity_sha256", "")
    ):
        issues.append("static metadata/axes/tile-plan checksum mismatch")
    try:
        metadata = json.loads(definition_json)
    except json.JSONDecodeError:
        issues.append("definition metadata is not valid JSON")
        return issues
    shape = tuple(int(value) for value in metadata["field_shape_theta2_theta1"])
    if (
        source["field/values"].shape != shape
        or source["field/status"].shape != shape
        or source["field/execution_route"].shape != shape
    ):
        issues.append("field dataset shape/orientation mismatch")
    if source["field/values"].dtype != np.dtype("<f8"):
        issues.append("scalar dtype mismatch")
    if source["field/status"].dtype != np.dtype("u1"):
        issues.append("status dtype mismatch")
    if source["field/execution_route"].dtype != np.dtype("u1"):
        issues.append("execution-route dtype mismatch")
    if _decode_string(source["field/values"].attrs.get("orientation", "")) != ORIENTATION:
        issues.append("field orientation metadata mismatch")
    if not bool(source["field/values"].attrs.get("authoritative", False)):
        issues.append("scalar field is not marked authoritative")
    if _decode_string(
        source["field/status"].attrs.get("vocabulary_json", "")
    ) != _canonical_json(metadata["status_vocabulary"]):
        issues.append("status vocabulary metadata mismatch")
    if _decode_string(
        source["field/execution_route"].attrs.get("vocabulary_json", "")
    ) != _canonical_json(metadata["execution_route_vocabulary"]):
        issues.append("execution-route vocabulary metadata mismatch")
    theta1_unit = _decode_string(source["axes/theta1"].attrs.get("unit", ""))
    theta2_unit = _decode_string(source["axes/theta2"].attrs.get("unit", ""))
    if theta1_unit != metadata["coordinate_unit"] or theta2_unit != metadata[
        "coordinate_unit"
    ]:
        issues.append("axis unit metadata mismatch")
    try:
        normalized = tuple(tuple(int(value) for value in row) for row in bounds)
        _validate_tile_plan(shape, normalized)
    except ValueError as error:
        issues.append(str(error))
    tile_count = len(bounds)
    tile_datasets = (
        "identity",
        "state",
        "checksum",
        "attempt",
        "evaluation_seconds",
        "diagnostics_json",
        "provenance_json",
        "exceptional_cells_json",
    )
    if any(len(source[f"tiles/{name}"]) != tile_count for name in tile_datasets):
        issues.append("tile metadata arrays have inconsistent lengths")
    else:
        static_digest = _decode_string(source.attrs["static_integrity_sha256"])
        for tile_index, tile_bounds in enumerate(bounds):
            expected_identity = _tile_identity(static_digest, tile_bounds)
            if _decode_string(source["tiles/identity"][tile_index]) != expected_identity:
                issues.append(f"tile {tile_index} identity mismatch")
        states = {int(value) for value in source["tiles/state"]}
        if not states.issubset({int(state) for state in TileState}):
            issues.append("tile state vocabulary mismatch")
    theta1 = np.asarray(source["axes/theta1"])
    theta2 = np.asarray(source["axes/theta2"])
    if np.any(np.diff(theta1) <= 0.0) or np.any(np.diff(theta2) <= 0.0):
        issues.append("stored axes are not strictly increasing")
    if metadata["periodic"] and (
        np.any(theta1 < -math.pi)
        or np.any(theta1 >= math.pi)
        or np.any(theta2 < -math.pi)
        or np.any(theta2 >= math.pi)
        or metadata["periodic_interval"] != "[-pi, pi)"
    ):
        issues.append("stored periodic axes violate [-pi, pi)")
    return issues


def discover_resume_state(path: Path) -> ResumeState:
    """Classify stored work units without invoking any dynamics evaluator."""

    completed: list[int] = []
    writing: list[int] = []
    not_started: list[int] = []
    corrupt: list[int] = []
    with h5py.File(path, "r") as source:
        static_issues = _static_issues(source)
        if static_issues:
            raise IntegrityError("; ".join(static_issues))
        for tile_index, raw_state in enumerate(source["tiles/state"]):
            state = TileState(int(raw_state))
            if state is TileState.NOT_STARTED:
                not_started.append(tile_index)
            elif state is TileState.WRITING:
                writing.append(tile_index)
            else:
                stored = _decode_string(source["tiles/checksum"][tile_index])
                try:
                    actual = _checksum_from_file(source, tile_index)
                except (OSError, ValueError):
                    corrupt.append(tile_index)
                else:
                    if stored and stored == actual:
                        completed.append(tile_index)
                    else:
                        corrupt.append(tile_index)
    return ResumeState(
        completed_tile_indices=tuple(completed),
        writing_tile_indices=tuple(writing),
        not_started_tile_indices=tuple(not_started),
        corrupt_tile_indices=tuple(corrupt),
    )


def read_tile_attempts(path: Path) -> tuple[int, ...]:
    """Return persisted attempt counters without changing completion state."""

    with h5py.File(path, "r") as source:
        return tuple(int(value) for value in source["tiles/attempt"])


def assert_dataset_compatible(
    path: Path,
    definition: FieldDefinition,
    tile_bounds: Sequence[object],
) -> ResumeState:
    """Fail closed unless an existing artifact matches a requested run exactly."""

    normalized_bounds = tuple(
        _normalize_bounds(bounds, definition.field_shape) for bounds in tile_bounds
    )
    _validate_tile_plan(definition.field_shape, normalized_bounds)
    expected_definition = _canonical_json(_definition_metadata(definition))
    expected_theta1 = np.asarray(definition.theta1_axis, dtype="<f8")
    expected_theta2 = np.asarray(definition.theta2_axis, dtype="<f8")
    expected_bounds = np.asarray(normalized_bounds, dtype="<i8")
    expected_digest = _static_integrity_digest(
        expected_definition,
        expected_theta1,
        expected_theta2,
        expected_bounds,
    )
    try:
        with h5py.File(path, "r") as source:
            matches = (
                _decode_string(source.attrs.get("definition_json", ""))
                == expected_definition
                and _decode_string(
                    source.attrs.get("static_integrity_sha256", "")
                )
                == expected_digest
                and np.array_equal(source["axes/theta1"], expected_theta1)
                and np.array_equal(source["axes/theta2"], expected_theta2)
                and np.array_equal(source["tiles/bounds"], expected_bounds)
            )
    except (KeyError, OSError) as error:
        raise IntegrityError(f"Existing field cannot be inspected: {error}") from error
    if not matches:
        raise IntegrityError(
            "Existing field definition, axes, provenance, or tile plan differs "
            "from the requested run."
        )
    resume = discover_resume_state(path)
    if resume.corrupt_tile_indices:
        raise IntegrityError(
            "Existing field contains corrupt completed tiles: "
            f"{list(resume.corrupt_tile_indices)}"
        )
    return resume


def validate_dataset(path: Path) -> DatasetValidation:
    issues: list[str] = []
    try:
        resume = discover_resume_state(path)
    except (OSError, IntegrityError) as error:
        return DatasetValidation(
            accepted=False,
            issues=(str(error),),
            resume_state=ResumeState((), (), (), ()),
        )
    if resume.corrupt_tile_indices:
        issues.append(
            "checksum mismatch in completed tiles: "
            f"{list(resume.corrupt_tile_indices)}"
        )
    with h5py.File(path, "r") as source:
        valid_route_codes = _route_codes(source) - {0}
        for tile_index in resume.completed_tile_indices:
            bounds = source["tiles/bounds"][tile_index]
            region = _tile_slice(bounds)
            status = np.asarray(source["field/status"][region])
            route = np.asarray(source["field/execution_route"][region])
            values = np.asarray(source["field/values"][region])
            status_values = {int(value) for value in np.unique(status)}
            if np.any(status == 0) or not status_values.issubset({1, 2, 3}):
                issues.append(f"completed tile {tile_index} has invalid cell states")
            if not set(int(value) for value in np.unique(route)).issubset(valid_route_codes):
                issues.append(f"completed tile {tile_index} has invalid route codes")
            if np.any(~np.isfinite(values[status == CellState.COMPLETED_VALID])):
                issues.append(f"completed tile {tile_index} has non-finite valid values")
            if np.any(~np.isnan(values[status == CellState.EXECUTION_ERROR])):
                issues.append(f"completed tile {tile_index} retains an error value")
    return DatasetValidation(not issues, tuple(issues), resume)


def read_authoritative_field(path: Path) -> FieldSnapshot:
    """Read completed, checksum-valid tiles and mask every other cell."""

    resume = discover_resume_state(path)
    with h5py.File(path, "r") as source:
        metadata = json.loads(_decode_string(source.attrs["definition_json"]))
        values = np.asarray(source["field/values"], dtype="<f8").copy()
        status = np.asarray(source["field/status"], dtype=np.uint8).copy()
        route = np.asarray(source["field/execution_route"], dtype=np.uint8).copy()
        authoritative = set(resume.completed_tile_indices)
        for tile_index, bounds in enumerate(source["tiles/bounds"]):
            if tile_index not in authoritative:
                region = _tile_slice(bounds)
                values[region] = np.nan
                status[region] = np.uint8(CellState.NOT_YET_COMPUTED)
                route[region] = np.uint8(0)
        return FieldSnapshot(
            theta1_axis=np.asarray(source["axes/theta1"]).copy(),
            theta2_axis=np.asarray(source["axes/theta2"]).copy(),
            values=values,
            status=status,
            execution_route=route,
            resume_state=resume,
            metadata=metadata,
        )


def inspect_dataset(path: Path) -> dict[str, object]:
    """Return static, dynamics-independent inspection evidence."""

    validation = validate_dataset(path)
    snapshot = read_authoritative_field(path)
    return {
        "accepted": validation.accepted,
        "issues": list(validation.issues),
        "metadata": snapshot.metadata,
        "theta1_axis": snapshot.theta1_axis.tolist(),
        "theta2_axis": snapshot.theta2_axis.tolist(),
        "field_shape": list(snapshot.values.shape),
        "completed_tile_indices": list(
            snapshot.resume_state.completed_tile_indices
        ),
        "writing_tile_indices": list(snapshot.resume_state.writing_tile_indices),
        "not_started_tile_indices": list(
            snapshot.resume_state.not_started_tile_indices
        ),
        "corrupt_tile_indices": list(snapshot.resume_state.corrupt_tile_indices),
        "cell_state_counts": {
            label: int(np.sum(snapshot.status == code))
            for code, label in STATUS_VOCABULARY.items()
        },
    }
