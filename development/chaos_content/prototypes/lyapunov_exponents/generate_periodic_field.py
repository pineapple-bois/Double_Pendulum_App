"""Create or resume an authoritative periodic Lyapunov scalar field."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

if __package__:
    from .field_adapter import (
        run_periodic_lyapunov_field,
        validate_lyapunov_oracle_spots,
    )
else:
    REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
    if str(REPOSITORY_ROOT) not in sys.path:
        sys.path.insert(0, str(REPOSITORY_ROOT))
    from development.chaos_content.prototypes.lyapunov_exponents.field_adapter import (
        run_periodic_lyapunov_field,
        validate_lyapunov_oracle_spots,
    )


def _jsonable(value: object) -> object:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples-per-axis", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--create", action="store_true")
    mode.add_argument("--resume", action="store_true")
    arguments = parser.parse_args()
    run_mode = "create" if arguments.create else "resume"
    summary = run_periodic_lyapunov_field(
        arguments.output,
        arguments.samples_per_axis,
        mode=run_mode,
    )
    oracle = validate_lyapunov_oracle_spots(arguments.output)
    payload = _jsonable(
        {
            "run": asdict(summary),
            "oracle_validation": asdict(oracle),
        }
    )
    encoded = json.dumps(payload, indent=2, sort_keys=True)
    summary_path = arguments.output.with_suffix(".summary.json")
    summary_path.write_text(f"{encoded}\n", encoding="utf-8")
    print(encoded)
    if not summary.validation.accepted or not oracle.accepted:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
