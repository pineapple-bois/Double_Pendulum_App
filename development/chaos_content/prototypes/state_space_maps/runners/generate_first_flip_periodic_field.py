"""Create or resume an authoritative periodic first-flip scalar field."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Sequence

from .generate_lyapunov_periodic_field import ConsoleProgressReporter
from ..src.first_flip.field_adapter import (
    FirstFlipFieldSpec,
    periodic_first_flip_field_definition,
    run_periodic_first_flip_field,
    summarize_persisted_first_flip_field,
    validate_first_flip_reference_spots,
)
from ..src.generation import accepted_process_execution_spec


PROTOTYPE_ROOT = Path(__file__).resolve().parents[1]
PILOT_OUTPUT_DIRECTORY = PROTOTYPE_ROOT / "outputs" / "first_flip_pilot"


def _horizon_token(observation_horizon_seconds: float) -> str:
    horizon = float(observation_horizon_seconds)
    if not math.isfinite(horizon) or horizon <= 0.0:
        raise ValueError("observation_horizon_seconds must be positive and finite")
    return format(horizon, ".12g").replace(".", "p")


def default_output_path(
    samples_per_axis: int,
    observation_horizon_seconds: float,
) -> Path:
    if samples_per_axis <= 0:
        raise ValueError("samples_per_axis must be positive")
    token = _horizon_token(observation_horizon_seconds)
    return PILOT_OUTPUT_DIRECTORY / f"first_flip_field_{samples_per_axis}_T{token}s.h5"


def manifest_path(output_path: Path) -> Path:
    return Path(output_path).with_suffix(".json")


def _jsonable(value: object) -> object:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def build_manifest(
    *,
    output_path: Path,
    definition,
    execution,
    run_summary,
    field_summary,
    spot_validation,
    completed_at_utc: str,
    operation_wall_seconds: float,
) -> dict[str, object]:
    from ..src.generation.hdf5 import ORIENTATION, SCHEMA_NAME, SCHEMA_VERSION

    return {
        "manifest_version": 1,
        "artifact": {
            "authoritative_hdf5": True,
            "hdf5_path": str(output_path),
            "json_path": str(manifest_path(output_path)),
        },
        "field": {
            "resolution_theta1_theta2": list(definition.resolution),
            "shape_theta2_theta1": list(definition.field_shape),
            "cell_count": definition.field_shape[0] * definition.field_shape[1],
            "stored_orientation": ORIENTATION,
            "periodic_interval": definition.periodic_interval,
        },
        "scientific_contract": {
            "observable": dict(definition.observable_provenance),
            "physical_parameters": dict(definition.physical_parameters),
            "numerical_parameters": dict(definition.numerical_parameters),
            "evaluator": dict(definition.evaluator_provenance),
        },
        "execution": {
            "process_policy": asdict(execution),
            "work_unit_shape_theta2_theta1": list(definition.nominal_tile_shape),
        },
        "persistence": {
            "schema_name": SCHEMA_NAME,
            "schema_version": SCHEMA_VERSION,
            "coordinator_owned_writes": True,
            "resumable_and_checksummed": True,
            "censoring_representation": (
                "completed-valid value == dimensionless horizon"
            ),
        },
        "software_provenance": dict(definition.software_provenance),
        "completion": {
            "completed_at_utc": completed_at_utc,
            "operation_wall_seconds": operation_wall_seconds,
            "generation_cells_per_second": run_summary.cells_per_second,
        },
        "run_summary": asdict(run_summary),
        "pilot_statistics": asdict(field_summary),
        "stricter_solver_spot_validation": asdict(spot_validation),
    }


def write_manifest(output_path: Path, payload: dict[str, object]) -> Path:
    path = manifest_path(output_path)
    encoded = json.dumps(
        _jsonable(payload), indent=2, sort_keys=True, allow_nan=False
    )
    path.write_text(f"{encoded}\n", encoding="utf-8")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples-per-axis", type=int, required=True, metavar="N")
    parser.add_argument(
        "--observation-horizon-seconds",
        type=float,
        required=True,
        metavar="SECONDS",
    )
    parser.add_argument("--output", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--create", action="store_true")
    mode.add_argument("--resume", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    mode = "create" if arguments.create else "resume"
    spec = FirstFlipFieldSpec(
        observation_horizon_seconds=arguments.observation_horizon_seconds
    )
    output_path = arguments.output or default_output_path(
        arguments.samples_per_axis,
        arguments.observation_horizon_seconds,
    )
    execution = accepted_process_execution_spec()
    definition = periodic_first_flip_field_definition(
        arguments.samples_per_axis, spec
    )
    progress = ConsoleProgressReporter(definition.field_shape, execution.process_width)
    started = perf_counter()
    summary = run_periodic_first_flip_field(
        output_path,
        arguments.samples_per_axis,
        mode=mode,
        spec=spec,
        execution=execution,
        progress_callback=progress,
    )
    if not summary.validation.accepted:
        return 1
    field_summary = summarize_persisted_first_flip_field(output_path)
    print("Checking nine persisted cells with stricter solver tolerances...", flush=True)
    spot_validation = validate_first_flip_reference_spots(output_path, spec)
    if not spot_validation.accepted:
        return 1
    payload = build_manifest(
        output_path=output_path,
        definition=definition,
        execution=execution,
        run_summary=summary,
        field_summary=field_summary,
        spot_validation=spot_validation,
        completed_at_utc=datetime.now(timezone.utc).isoformat(),
        operation_wall_seconds=perf_counter() - started,
    )
    sidecar = write_manifest(output_path, payload)
    print(f"Manifest written: {sidecar}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
