"""Validate late and worst-drift cells in a saved long-horizon investigation."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import numpy as np

from .first_flip_horizon_and_energy_accessibility import (
    NativeCellResult,
    STATUS_OBSERVED,
    _comparison,
)
from ...src.first_flip.reference import gravity_timescale
from ...src.lyapunov.reference import PendulumParameters


HERE = Path(__file__).resolve().parent
DEFAULT_ARRAYS = (
    HERE / "evidence" / "first_flip_horizon_128_through_H1000_exploratory.npz"
)
DEFAULT_OUTPUT = HERE / "evidence" / "first_flip_H1000_tail_validation.json"


def _native_from_arrays(
    source: np.lib.npyio.NpzFile,
    horizon_index: int,
    theta2_index: int,
    theta1_index: int,
    axis_size: int,
) -> NativeCellResult:
    def scalar(name: str) -> object:
        return source[f"h{horizon_index}_{name}"][theta2_index, theta1_index]

    return NativeCellResult(
        index=theta2_index * axis_size + theta1_index,
        status=int(scalar("status")),
        event_time_seconds=float(scalar("event_time_seconds")),
        event_index=int(scalar("event_index")),
        event_state=tuple(
            float(value)
            for value in source[f"h{horizon_index}_event_state"][
                theta2_index, theta1_index
            ]
        ),
        integration_endpoint_seconds=float(scalar("integration_endpoint_seconds")),
        rhs_evaluations=int(scalar("rhs_evaluations")),
        accepted_point_count=int(scalar("accepted_point_count")),
        maximum_normalized_energy_drift=float(
            scalar("maximum_normalized_energy_drift")
        ),
        maximum_accepted_angular_increment=float(
            scalar("maximum_accepted_angular_increment")
        ),
        triggering_surface_residual=float(scalar("triggering_surface_residual")),
        maximum_solver_step_seconds=float(scalar("maximum_solver_step_seconds")),
        wall_seconds=float(scalar("cell_wall_seconds")),
    )


def validate_tail(arrays_path: Path = DEFAULT_ARRAYS) -> dict[str, object]:
    parameters = PendulumParameters()
    time_scale = gravity_timescale(parameters)
    source = np.load(arrays_path)
    axis = source["theta_axis_radians"]
    horizons = source["horizons_hat"]
    selected_horizons = tuple(
        index for index, value in enumerate(horizons) if value in (100.0, 1000.0)
    )
    if len(selected_horizons) != 2:
        raise ValueError("saved arrays must contain both T_hat=100 and T_hat=1000")
    cases: list[dict[str, object]] = []
    for horizon_index in selected_horizons:
        status = source[f"h{horizon_index}_status"]
        times = source[f"h{horizon_index}_event_time_seconds"]
        drifts = source[f"h{horizon_index}_maximum_normalized_energy_drift"]
        observed_indices = np.argwhere(status == STATUS_OBSERVED)
        latest = tuple(
            observed_indices[np.argmax(times[status == STATUS_OBSERVED])]
        )
        worst = tuple(np.unravel_index(np.nanargmax(drifts), drifts.shape))
        for role, (theta2_index, theta1_index) in (
            ("latest_observed", latest),
            ("maximum_energy_drift", worst),
        ):
            native = _native_from_arrays(
                source,
                horizon_index,
                int(theta2_index),
                int(theta1_index),
                len(axis),
            )
            cases.append(
                _comparison(
                    f"H{horizons[horizon_index]:g}_{role}",
                    float(axis[theta1_index]),
                    float(axis[theta2_index]),
                    float(horizons[horizon_index] * time_scale),
                    native,
                )
            )
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "late-tail and worst-energy native-vs-trusted validation",
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "source_arrays": str(arrays_path.relative_to(HERE)),
        "source_arrays_sha256": hashlib.sha256(arrays_path.read_bytes()).hexdigest(),
        "case_count": len(cases),
        "passed_count": sum(bool(item["accepted"]) for item in cases),
        "accepted": all(bool(item["accepted"]) for item in cases),
        "cases": cases,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arrays", type=Path, default=DEFAULT_ARRAYS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args(argv)
    payload = validate_tail(arguments.arrays)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"accepted": payload["accepted"], "cases": payload["cases"]}, indent=2))
    # A rejected exploratory decade is the expected scientific result and is
    # represented in the evidence payload, not as a tool-execution failure.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
