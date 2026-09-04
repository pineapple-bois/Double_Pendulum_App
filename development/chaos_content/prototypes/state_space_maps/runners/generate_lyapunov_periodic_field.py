"""Create or resume an authoritative periodic Lyapunov scalar field."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from dataclasses import asdict
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from ..src.generation import (
        FieldDefinition,
        FieldProgress,
        FieldRunSummary,
        ProcessExecutionSpec,
    )
    from ..src.lyapunov.field_adapter import LyapunovOracleValidation

PROTOTYPE_ROOT = Path(__file__).resolve().parents[1]
OPERATIONAL_OUTPUT_DIRECTORY = PROTOTYPE_ROOT / "outputs" / "finite_time_field"


def default_output_path(samples_per_axis: int) -> Path:
    """Return the stable operational HDF5 path for one square resolution."""

    if samples_per_axis <= 0:
        raise ValueError("samples_per_axis must be positive.")
    return (
        OPERATIONAL_OUTPUT_DIRECTORY
        / f"finite_time_field_{samples_per_axis}.h5"
    )


def manifest_path(output_path: Path) -> Path:
    """Return the human-readable sidecar path for one authoritative field."""

    return Path(output_path).with_suffix(".json")


def _jsonable(value: object) -> object:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _format_duration(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


class ConsoleProgressReporter:
    """Print initial state and approximately ten-percent progress milestones."""

    def __init__(
        self,
        field_shape: tuple[int, int],
        process_width: int,
    ) -> None:
        self.field_shape = field_shape
        self.process_width = process_width
        self._announced = False
        self._last_decile = -1

    def __call__(self, progress: FieldProgress) -> None:
        percent = 100.0 * (
            progress.completed_work_units / progress.total_work_units
        )
        decile = min(10, int(percent // 10.0))
        if not self._announced:
            action = "Generating" if progress.mode == "create" else "Resuming"
            print(f"{action} {progress.output_path.name}", flush=True)
            theta2_samples, theta1_samples = self.field_shape
            print(
                f"{theta1_samples} × {theta2_samples} field | "
                f"{progress.total_cells} cells | "
                f"{progress.total_work_units} work units | "
                f"{self.process_width} workers",
                flush=True,
            )
            if progress.mode == "resume":
                print(
                    f"{progress.completed_work_units}/"
                    f"{progress.total_work_units} work units already complete "
                    f"({percent:.1f}%)",
                    flush=True,
                )
                print(
                    f"{progress.total_work_units - progress.completed_work_units} "
                    "work units remaining",
                    flush=True,
                )
            self._announced = True
            self._last_decile = decile
            if progress.completed_work_units != progress.total_work_units:
                return

        if decile <= self._last_decile and (
            progress.completed_work_units != progress.total_work_units
        ):
            return
        self._last_decile = decile
        if progress.evaluated_cells and progress.elapsed_seconds > 0.0:
            rate = progress.evaluated_cells / progress.elapsed_seconds
            remaining_cells = progress.total_cells - progress.completed_cells
            eta = _format_duration(remaining_cells / rate)
            rate_text = f"{rate:.1f} cells/s"
            eta_text = f"ETA ~{eta}"
        else:
            rate_text = "throughput pending"
            eta_text = "ETA ~unknown"
        print(
            f"[{percent:5.1f}%] "
            f"{progress.completed_work_units}/{progress.total_work_units} work units | "
            f"{progress.completed_cells}/{progress.total_cells} cells | "
            f"{_format_duration(progress.elapsed_seconds)} elapsed | "
            f"{rate_text} | {eta_text}",
            flush=True,
        )


def build_manifest(
    *,
    output_path: Path,
    definition: FieldDefinition,
    execution: ProcessExecutionSpec,
    summary: FieldRunSummary,
    oracle: LyapunovOracleValidation,
    completed_at_utc: str,
    operation_wall_seconds: float,
) -> dict[str, object]:
    """Build a human-readable manifest from the objects used by the run."""

    from ..src.generation.hdf5 import ORIENTATION, SCHEMA_NAME, SCHEMA_VERSION

    numerical = dict(definition.numerical_parameters)
    total_work_units = summary.completed_tiles_after + summary.pending_tiles_after
    return {
        "manifest_version": 1,
        "artifact": {
            "authoritative_hdf5": True,
            "hdf5_name": output_path.name,
            "hdf5_path": str(output_path),
            "json_path": str(manifest_path(output_path)),
        },
        "field": {
            "samples_per_axis": definition.resolution[0],
            "shape_theta2_theta1": list(definition.field_shape),
            "cell_count": definition.field_shape[0] * definition.field_shape[1],
            "coordinate_unit": definition.coordinate_unit,
            "periodic": definition.periodic,
            "periodic_interval": definition.periodic_interval,
            "stored_orientation": ORIENTATION,
        },
        "scientific_contract": {
            "observable": dict(definition.observable_provenance),
            "metric": {
                "convention": "Candidate-A",
                "characteristic_length": numerical[
                    "candidate_a_characteristic_length"
                ],
            },
            "physical_parameters": dict(definition.physical_parameters),
            "numerical_parameters": numerical,
            "evaluator": dict(definition.evaluator_provenance),
        },
        "execution": {
            "process_policy": asdict(execution),
            "work_unit_shape_theta2_theta1": list(
                definition.nominal_tile_shape
            ),
            "work_unit_count": total_work_units,
            "worker_recycling_policy": {
                "maximum_cells_per_pool": execution.maximum_cells_per_pool,
                "observed_pool_count": summary.pool_count,
                "observed_recycling_events": summary.recycling_events,
            },
        },
        "persistence": {
            "schema_name": SCHEMA_NAME,
            "schema_version": SCHEMA_VERSION,
            "coordinator_owned_writes": True,
            "resume_artifact": output_path.name,
        },
        "software_provenance": dict(definition.software_provenance),
        "completion": {
            "completed_at_utc": completed_at_utc,
            "operation_wall_seconds_including_oracle_validation": (
                operation_wall_seconds
            ),
            "generation_cells_per_second": summary.cells_per_second,
            "route_counts": summary.validation.route_counts,
            "status_counts": summary.validation.status_counts,
            "completed_invalid_cells": summary.validation.status_counts.get(
                "completed_invalid", 0
            ),
            "execution_error_cells": summary.validation.status_counts.get(
                "execution_error", 0
            ),
        },
        "run_summary": asdict(summary),
        "oracle_validation": asdict(oracle),
    }


def write_manifest(output_path: Path, payload: dict[str, object]) -> Path:
    """Write the optional human-readable sidecar after successful validation."""

    path = manifest_path(output_path)
    encoded = json.dumps(
        _jsonable(payload),
        indent=2,
        sort_keys=True,
        allow_nan=False,
    )
    path.write_text(f"{encoded}\n", encoding="utf-8")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--samples-per-axis",
        type=int,
        required=True,
        metavar="N",
        help=(
            "Samples on each angular axis. This determines the square field "
            "shape and default resolution-specific output name."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        help=(
            "Authoritative HDF5 destination. By default this is the operational "
            "outputs/finite_time_field/finite_time_field_<samples>.h5 path."
        ),
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=5.0,
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--create", action="store_true")
    mode.add_argument("--resume", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    from ..src.generation import accepted_process_execution_spec
    from ..src.lyapunov.field_adapter import (
        periodic_lyapunov_field_definition,
        run_periodic_lyapunov_field,
        validate_lyapunov_oracle_spots,
    )
    from ..src.lyapunov.reference import RenormalizedTangentSpec

    run_mode = "create" if arguments.create else "resume"
    output_path = arguments.output or default_output_path(
        arguments.samples_per_axis
    )
    specification = RenormalizedTangentSpec(
        duration=arguments.duration,
    )
    execution = accepted_process_execution_spec()
    definition = periodic_lyapunov_field_definition(
        arguments.samples_per_axis,
        specification,
    )
    progress = ConsoleProgressReporter(
        definition.field_shape,
        execution.process_width,
    )
    operation_started = perf_counter()
    summary = run_periodic_lyapunov_field(
        output_path,
        arguments.samples_per_axis,
        mode=run_mode,
        spec=specification,
        execution=execution,
        progress_callback=progress,
    )
    print("Validating persisted field against established oracle spots...", flush=True)
    oracle = validate_lyapunov_oracle_spots(output_path)
    if not summary.validation.accepted or not oracle.accepted:
        return 1
    payload = build_manifest(
        output_path=output_path,
        definition=definition,
        execution=execution,
        summary=summary,
        oracle=oracle,
        completed_at_utc=datetime.now(timezone.utc).isoformat(),
        operation_wall_seconds=perf_counter() - operation_started,
    )
    path = write_manifest(output_path, payload)
    print(f"Manifest written: {path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
