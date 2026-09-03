"""Create or resume an authoritative periodic Lyapunov scalar field."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

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


def _jsonable(value: object) -> object:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples-per-axis", type=int, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        help=(
            "Authoritative HDF5 destination. By default this is the operational "
            "outputs/finite_time_field/finite_time_field_<samples>.h5 path."
        ),
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--create", action="store_true")
    mode.add_argument("--resume", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    from ..src.lyapunov.field_adapter import (
        run_periodic_lyapunov_field,
        validate_lyapunov_oracle_spots,
    )

    run_mode = "create" if arguments.create else "resume"
    output_path = arguments.output or default_output_path(
        arguments.samples_per_axis
    )
    summary = run_periodic_lyapunov_field(
        output_path,
        arguments.samples_per_axis,
        mode=run_mode,
    )
    oracle = validate_lyapunov_oracle_spots(output_path)
    payload = _jsonable(
        {
            "run": asdict(summary),
            "oracle_validation": asdict(oracle),
        }
    )
    encoded = json.dumps(payload, indent=2, sort_keys=True)
    print(encoded)
    if not summary.validation.accepted or not oracle.accepted:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
