"""Three-pair 64x64 operational A/B for native first-flip acceptance."""

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

from ....src.first_flip.field_adapter import (
    FirstFlipFieldSpec,
    run_periodic_first_flip_field,
    summarize_persisted_first_flip_field,
    validate_first_flip_reference_spots,
)
from ....src.first_flip.native_artifacts import FIRST_FLIP_NATIVE_CACHE_ENVIRONMENT
from ....src.first_flip.native_runtime import first_flip_native_provenance
from ....src.generation import CellState, accepted_process_execution_spec, read_authoritative_field


PERFORMANCE_DIRECTORY = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PERFORMANCE_DIRECTORY / "evidence/current/first_flip_native_field_validation_64.json"
ORDERS = (("native", "compiled"), ("compiled", "native"), ("native", "compiled"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(*arguments: str) -> str:
    result = subprocess.run(["git", *arguments], capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def _route_counts(path: Path) -> dict[str, int]:
    snapshot = read_authoritative_field(path)
    vocabulary = snapshot.metadata["execution_route_vocabulary"]
    return {
        str(vocabulary[str(int(code))] if str(int(code)) in vocabulary else vocabulary[int(code)]): int(np.count_nonzero(snapshot.execution_route == code))
        for code in np.unique(snapshot.execution_route)
    }


def _run(label: str, path: Path, spec: FirstFlipFieldSpec) -> dict[str, object]:
    started = perf_counter()
    summary = run_periodic_first_flip_field(
        path,
        64,
        mode="create",
        spec=spec,
        force_compiled=label == "compiled",
        enable_native_candidate=label == "native",
    )
    outer_wall = perf_counter() - started
    field = summarize_persisted_first_flip_field(path)
    spots = validate_first_flip_reference_spots(path, spec)
    return {
        "outer_wall_seconds": outer_wall,
        "cells_per_second": 4096 / outer_wall,
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
        "route_counts": _route_counts(path),
        "stricter_spots": asdict(spots),
        "hdf5_sha256": _sha256(path),
    }


def _compare(native_path: Path, compiled_path: Path, spec: FirstFlipFieldSpec) -> dict[str, object]:
    native = read_authoritative_field(native_path)
    compiled = read_authoritative_field(compiled_path)
    cap = spec.dimensionless_observation_horizon
    native_valid = native.status == CellState.COMPLETED_VALID
    compiled_valid = compiled.status == CellState.COMPLETED_VALID
    native_censored = native_valid & (native.values == cap)
    compiled_censored = compiled_valid & (compiled.values == cap)
    native_observed = native_valid & (native.values < cap)
    compiled_observed = compiled_valid & (compiled.values < cap)
    maximum_difference = float(
        np.max(np.abs(native.values[native_observed] - compiled.values[native_observed]))
        * spec.gravity_timescale_seconds
    )
    checks = {
        "axes_identical": np.array_equal(native.theta1_axis, compiled.theta1_axis) and np.array_equal(native.theta2_axis, compiled.theta2_axis),
        "statuses_identical": np.array_equal(native.status, compiled.status),
        "observed_masks_identical": np.array_equal(native_observed, compiled_observed),
        "censor_masks_identical": np.array_equal(native_censored, compiled_censored),
        "zero_invalid_or_errors": bool(np.all(native_valid) and np.all(compiled_valid)),
        "observed_times_within_gate": maximum_difference <= 5.0e-8,
        "native_routes_only": set(np.unique(native.execution_route)) == {3},
        "compiled_routes_only": set(np.unique(compiled.execution_route)) == {2},
    }
    return {
        **checks,
        "accepted": all(checks.values()),
        "maximum_observed_event_time_difference_seconds": maximum_difference,
        "observed_count": int(np.count_nonzero(native_observed)),
        "censored_count": int(np.count_nonzero(native_censored)),
    }


def run() -> dict[str, object]:
    spec = FirstFlipFieldSpec()
    previous_numba = os.environ.get("NUMBA_CACHE_DIR")
    previous_native = os.environ.get(FIRST_FLIP_NATIVE_CACHE_ENVIRONMENT)
    try:
        with tempfile.TemporaryDirectory(prefix="first-flip-native-field-validation-") as name:
            root = Path(name)
            os.environ["NUMBA_CACHE_DIR"] = str(root / "numba-cache")
            os.environ[FIRST_FLIP_NATIVE_CACHE_ENVIRONMENT] = str(root / "native-cache")
            pairs = []
            for index, order in enumerate(ORDERS, 1):
                directory = root / f"pair-{index}"
                directory.mkdir()
                records = {}
                for label in order:
                    records[label] = _run(label, directory / f"{label}.h5", spec)
                comparison = _compare(directory / "native.h5", directory / "compiled.h5", spec)
                pairs.append({
                    "pair": index,
                    "order": list(order),
                    **records,
                    "comparison": comparison,
                    "whole_field_speedup": records["compiled"]["outer_wall_seconds"] / records["native"]["outer_wall_seconds"],
                    "evaluation_speedup": records["compiled"]["runner"]["evaluation_seconds"] / records["native"]["runner"]["evaluation_seconds"],
                })
    finally:
        if previous_numba is None:
            os.environ.pop("NUMBA_CACHE_DIR", None)
        else:
            os.environ["NUMBA_CACHE_DIR"] = previous_numba
        if previous_native is None:
            os.environ.pop(FIRST_FLIP_NATIVE_CACHE_ENVIRONMENT, None)
        else:
            os.environ[FIRST_FLIP_NATIVE_CACHE_ENVIRONMENT] = previous_native
    whole = [float(pair["whole_field_speedup"]) for pair in pairs]
    evaluation = [float(pair["evaluation_speedup"]) for pair in pairs]
    operational = all(
        pair[route]["runner"]["validation"]["accepted"]
        and pair[route]["stricter_spots"]["accepted"]
        and pair[route]["runner"]["all_workers_stopped"]
        for pair in pairs for route in ("native", "compiled")
    )
    scientific = all(pair["comparison"]["accepted"] for pair in pairs)
    accepted = operational and scientific and statistics.median(whole) >= 1.5
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python": platform.python_version(), "platform": platform.platform(),
            "numpy": np.__version__, "scipy": scipy.__version__, "numba": numba.__version__,
            "git_head": _git("rev-parse", "HEAD"), "git_status": _git("status", "--short"),
        },
        "workload": {"samples_per_axis": 64, "cell_count": 4096, "duration_seconds": 5.0, "orders": [list(order) for order in ORDERS], "execution": asdict(accepted_process_execution_spec())},
        "native_provenance": first_flip_native_provenance(),
        "pairs": pairs,
        "median_whole_field_speedup": statistics.median(whole),
        "median_evaluation_speedup": statistics.median(evaluation),
        "acceptance": {"scientific": scientific, "operational": operational, "median_speedup_at_least_1_5": statistics.median(whole) >= 1.5, "accepted": accepted},
        "source_sha256": {str(Path(__file__)): _sha256(Path(__file__))},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    options = parser.parse_args()
    if options.output.exists():
        raise FileExistsError(f"Refusing to replace benchmark evidence: {options.output}")
    payload = run()
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"median_whole_field_speedup": payload["median_whole_field_speedup"], "median_evaluation_speedup": payload["median_evaluation_speedup"], "acceptance": payload["acceptance"]}, indent=2))
    return 0 if payload["acceptance"]["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
