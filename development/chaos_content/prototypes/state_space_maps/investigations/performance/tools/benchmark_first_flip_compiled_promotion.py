"""Three-pair 64x64 operational A/B for compiled first-flip promotion."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import statistics
import subprocess
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import numba
import numpy as np
import scipy

from ....src.first_flip.compiled import first_flip_compiled_provenance
from ....src.first_flip.field_adapter import (
    FirstFlipFieldSpec,
    run_periodic_first_flip_field,
    summarize_persisted_first_flip_field,
    validate_first_flip_reference_spots,
)
from ....src.generation import accepted_process_execution_spec, read_authoritative_field


PERFORMANCE_DIRECTORY = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PERFORMANCE_DIRECTORY / "evidence/current/first_flip_compiled_promotion_64.json"
ORDERS = (("compiled", "trusted"), ("trusted", "compiled"), ("compiled", "trusted"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def _run(label: str, path: Path, spec: FirstFlipFieldSpec) -> dict[str, object]:
    started = perf_counter()
    summary = run_periodic_first_flip_field(
        path,
        64,
        mode="create",
        spec=spec,
        force_trusted=label == "trusted",
    )
    outer = perf_counter() - started
    field = summarize_persisted_first_flip_field(path)
    spots = validate_first_flip_reference_spots(path, spec)
    return {
        "outer_wall_seconds": outer,
        "cells_per_second": 4096 / outer,
        "runner": {
            "total_seconds": summary.total_seconds,
            "setup_seconds": summary.setup_seconds,
            "evaluation_seconds": summary.evaluation_seconds,
            "persistence_seconds": summary.persistence_seconds,
            "shutdown_seconds": summary.shutdown_seconds,
            "pool_count": summary.pool_count,
            "recycling_events": summary.recycling_events,
            "maximum_worker_peak_rss_bytes": summary.maximum_worker_peak_rss_bytes,
            "all_workers_stopped": summary.all_workers_stopped,
            "validation": asdict(summary.validation),
        },
        "field": asdict(field),
        "stricter_spots": asdict(spots),
        "hdf5_sha256": _sha256(path),
    }


def _compare(compiled_path: Path, trusted_path: Path, spec: FirstFlipFieldSpec) -> dict[str, object]:
    compiled = read_authoritative_field(compiled_path)
    trusted = read_authoritative_field(trusted_path)
    cap = spec.dimensionless_observation_horizon
    compiled_censored = compiled.values == cap
    trusted_censored = trusted.values == cap
    observed = ~compiled_censored
    maximum_time_difference = float(
        np.max(np.abs(compiled.values[observed] - trusted.values[observed]))
        * spec.gravity_timescale_seconds
    )
    checks = {
        "axes_identical": np.array_equal(compiled.theta1_axis, trusted.theta1_axis)
        and np.array_equal(compiled.theta2_axis, trusted.theta2_axis),
        "statuses_identical": np.array_equal(compiled.status, trusted.status),
        "censor_masks_identical": np.array_equal(compiled_censored, trusted_censored),
        "observed_times_within_gate": maximum_time_difference <= 5.0e-8,
        "compiled_routes_only": set(np.unique(compiled.execution_route)) == {2},
        "trusted_routes_only": set(np.unique(trusted.execution_route)) == {1},
    }
    return {
        **checks,
        "accepted": all(checks.values()),
        "maximum_observed_event_time_difference_seconds": maximum_time_difference,
        "observed_count": int(np.count_nonzero(observed)),
        "censored_count": int(np.count_nonzero(compiled_censored)),
    }


def run(output: Path) -> dict[str, object]:
    spec = FirstFlipFieldSpec()
    previous_cache = os.environ.get("NUMBA_CACHE_DIR")
    try:
        with tempfile.TemporaryDirectory(prefix="first-flip-promotion-") as name:
            root = Path(name)
            cache = root / "numba-cache"
            os.environ["NUMBA_CACHE_DIR"] = str(cache)
            pairs = []
            for index, order in enumerate(ORDERS, 1):
                directory = root / f"pair-{index}"
                directory.mkdir()
                records = {}
                for label in order:
                    records[label] = _run(label, directory / f"{label}.h5", spec)
                comparison = _compare(directory / "compiled.h5", directory / "trusted.h5", spec)
                pairs.append({
                    "order": list(order),
                    **records,
                    "comparison": comparison,
                    "speedup": records["trusted"]["outer_wall_seconds"] / records["compiled"]["outer_wall_seconds"],
                })
    finally:
        if previous_cache is None:
            os.environ.pop("NUMBA_CACHE_DIR", None)
        else:
            os.environ["NUMBA_CACHE_DIR"] = previous_cache
    speedups = [float(pair["speedup"]) for pair in pairs]
    accepted = (
        all(pair["comparison"]["accepted"] for pair in pairs)
        and all(pair[label]["runner"]["validation"]["accepted"] for pair in pairs for label in ("compiled", "trusted"))
        and all(pair[label]["stricter_spots"]["accepted"] for pair in pairs for label in ("compiled", "trusted"))
        and all(pair[label]["runner"]["all_workers_stopped"] for pair in pairs for label in ("compiled", "trusted"))
        and statistics.median(speedups) >= 1.5
    )
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python": platform.python_version(), "platform": platform.platform(),
            "numpy": np.__version__, "scipy": scipy.__version__, "numba": numba.__version__,
            "git_head": _git("rev-parse", "HEAD"), "git_status": _git("status", "--short"),
        },
        "workload": {"samples_per_axis": 64, "duration_seconds": 5.0, "orders": [list(x) for x in ORDERS], "execution": asdict(accepted_process_execution_spec())},
        "compiled_provenance": first_flip_compiled_provenance(),
        "pairs": pairs,
        "median_speedup": statistics.median(speedups),
        "acceptance": {"median_speedup_at_least_1_5": statistics.median(speedups) >= 1.5, "accepted": accepted},
        "source_sha256": {str(Path(__file__)): _sha256(Path(__file__))},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    options = parser.parse_args()
    if options.output.exists():
        raise FileExistsError(f"Refusing to replace benchmark: {options.output}")
    payload = run(options.output)
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"median_speedup": payload["median_speedup"], "acceptance": payload["acceptance"]}, indent=2))
    return 0 if payload["acceptance"]["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
