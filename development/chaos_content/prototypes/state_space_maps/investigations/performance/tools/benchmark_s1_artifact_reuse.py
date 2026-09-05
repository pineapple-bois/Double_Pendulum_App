"""Bounded acceptance experiment for build-once/load-many S1 artifacts."""

from __future__ import annotations

import argparse
import contextlib
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
from typing import Iterator, Mapping

import numba
import numpy as np
import scipy

from ....src.generation import accepted_process_execution_spec, read_authoritative_field
from ....src.generation import runner as runner_module
from ....src.generation.runner import run_scalar_field
from ....src.lyapunov.field_adapter import (
    lyapunov_evaluator_binding,
    periodic_lyapunov_field_definition,
)
from ....src.lyapunov.reference import RenormalizedTangentSpec
from ....src.lyapunov.s1 import (
    S1_ARTIFACT_CACHE_ENVIRONMENT,
    S1Artifact,
    s1_build_provenance,
    s1_build_support,
    s1_specification_eligibility,
)

from .benchmark_s1_field_level import (
    _compare_fields,
    _sha256,
    _summary_record,
    _tile_totals,
    trusted_evaluator_binding,
    trusted_field_definition,
)


PERFORMANCE_DIRECTORY = Path(__file__).resolve().parents[1]
PROTOTYPE_DIRECTORY = PERFORMANCE_DIRECTORY.parents[1]
DEFAULT_OUTPUT = (
    PERFORMANCE_DIRECTORY
    / "evidence"
    / "current"
    / "s1_build_once_load_many.json"
)
BASELINE_EVIDENCE = (
    PERFORMANCE_DIRECTORY
    / "evidence"
    / "current"
    / "s1_field_level_benchmark_128.json"
)
PAIR_ORDERS = (
    ("promoted_s1", "trusted_pre_s1"),
    ("trusted_pre_s1", "promoted_s1"),
    ("promoted_s1", "trusted_pre_s1"),
)


def _git_output(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        capture_output=True,
        check=False,
        text=True,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unavailable"


@contextlib.contextmanager
def _artifact_cache(path: Path) -> Iterator[None]:
    previous = os.environ.get(S1_ARTIFACT_CACHE_ENVIRONMENT)
    os.environ[S1_ARTIFACT_CACHE_ENVIRONMENT] = str(path.resolve())
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(S1_ARTIFACT_CACHE_ENVIRONMENT, None)
        else:
            os.environ[S1_ARTIFACT_CACHE_ENVIRONMENT] = previous


def _artifact_record(artifact: S1Artifact) -> dict[str, object]:
    return {
        "available": artifact.available,
        "key": artifact.key,
        "manifest_sha256": artifact.manifest_sha256,
        "native_library_sha256": artifact.native_library_sha256,
        "callback_artifact_sha256": dict(artifact.callback_artifact_sha256),
        "identity": dict(artifact.identity),
        "failure_type": artifact.failure_type,
        "failure_reason": artifact.failure_reason,
    }


def run_lifecycle_repetition(
    cache_directory: Path,
    *,
    pool_count: int = 8,
) -> dict[str, object]:
    spec = RenormalizedTangentSpec(duration=5.0)
    execution = accepted_process_execution_spec()
    with _artifact_cache(cache_directory):
        started = perf_counter()
        preparation_started = perf_counter()
        binding = lyapunov_evaluator_binding(spec)
        artifact_preparation = perf_counter() - preparation_started
        artifact = binding.initializer_arguments[1]
        if not isinstance(artifact, S1Artifact) or not artifact.available:
            raise RuntimeError("Acceptance lifecycle did not prepare an S1 artifact")
        pools: list[dict[str, object]] = []
        all_workers_stopped = True
        for index in range(pool_count):
            executor, identities, setup = runner_module._open_pool(binding, execution)
            shutdown, stopped = runner_module._close_pool(executor, identities)
            all_workers_stopped = all_workers_stopped and stopped
            pools.append(
                {
                    "index": index + 1,
                    "setup_seconds": setup,
                    "shutdown_seconds": shutdown,
                    "all_workers_stopped": stopped,
                    "worker_process_ids": [item.process_id for item in identities],
                    "worker_initialization_seconds": [
                        item.warmup_seconds for item in identities
                    ],
                    "worker_peak_rss_bytes": [item.peak_rss_bytes for item in identities],
                }
            )
        total_wall = perf_counter() - started
    setup_total = artifact_preparation + sum(
        float(pool["setup_seconds"]) for pool in pools
    )
    worker_initializations = [
        float(value)
        for pool in pools
        for value in pool["worker_initialization_seconds"]
    ]
    return {
        "artifact_preparation_seconds": artifact_preparation,
        "effective_eight_pool_setup_seconds": setup_total,
        "pool_setup_seconds": [pool["setup_seconds"] for pool in pools],
        "warm_pool_setup_median_seconds": statistics.median(
            float(pool["setup_seconds"]) for pool in pools[1:]
        ),
        "worker_initialization_median_seconds": statistics.median(
            worker_initializations
        ),
        "worker_initialization_range_seconds": [
            min(worker_initializations),
            max(worker_initializations),
        ],
        "maximum_worker_peak_rss_bytes": max(
            int(value)
            for pool in pools
            for value in pool["worker_peak_rss_bytes"]
        ),
        "all_workers_stopped": all_workers_stopped,
        "total_wall_including_shutdown_seconds": total_wall,
        "artifact": _artifact_record(artifact),
        "pools": pools,
    }


def run_lifecycle_experiment(
    root: Path,
    repetitions: int,
) -> dict[str, object]:
    records = [
        run_lifecycle_repetition(root / f"repetition-{index + 1}")
        for index in range(repetitions)
    ]
    totals = [
        float(record["effective_eight_pool_setup_seconds"])
        for record in records
    ]
    return {
        "repetitions": records,
        "median_effective_eight_pool_setup_seconds": statistics.median(totals),
    }


def _run_one_field(
    label: str,
    path: Path,
    samples: int,
    spec: RenormalizedTangentSpec,
) -> tuple[dict[str, object], float]:
    execution = accepted_process_execution_spec()
    if label == "promoted_s1":
        definition = periodic_lyapunov_field_definition(samples, spec)
        started = perf_counter()
        preparation_started = perf_counter()
        binding = lyapunov_evaluator_binding(spec)
        artifact_preparation = perf_counter() - preparation_started
    elif label == "trusted_pre_s1":
        definition = trusted_field_definition(samples, spec)
        binding = trusted_evaluator_binding(spec)
        artifact_preparation = 0.0
        started = perf_counter()
    else:  # pragma: no cover - fixed preregistered labels.
        raise ValueError(f"Unknown field label: {label}")
    summary = run_scalar_field(
        path,
        definition,
        binding,
        execution=execution,
        mode="create",
    )
    outer = perf_counter() - started
    record = {
        **_summary_record(summary, outer),
        **_tile_totals(path),
        "hdf5_sha256": _sha256(path),
        "artifact_preparation_seconds": artifact_preparation,
        "effective_setup_seconds": artifact_preparation + summary.setup_seconds,
    }
    if label == "promoted_s1":
        artifact = binding.initializer_arguments[1]
        if not isinstance(artifact, S1Artifact):
            raise RuntimeError("Promoted field binding has no S1 artifact descriptor")
        record["artifact"] = _artifact_record(artifact)
    return record, outer


def run_field_pair(
    directory: Path,
    cache_directory: Path,
    order: tuple[str, str],
    samples: int,
    duration: float,
) -> dict[str, object]:
    directory.mkdir(parents=True, exist_ok=False)
    spec = RenormalizedTangentSpec(duration=duration)
    paths = {
        "promoted_s1": directory / "promoted_s1.h5",
        "trusted_pre_s1": directory / "trusted_pre_s1.h5",
    }
    records: dict[str, dict[str, object]] = {}
    with _artifact_cache(cache_directory):
        for label in order:
            record, _outer = _run_one_field(
                label,
                paths[label],
                samples,
                spec,
            )
            records[label] = record
    promoted = read_authoritative_field(paths["promoted_s1"])
    trusted = read_authoritative_field(paths["trusted_pre_s1"])
    comparison = _compare_fields(promoted, trusted)
    if not comparison["accepted"]:
        raise RuntimeError(f"Persisted field comparison failed: {comparison}")
    return {
        "order": list(order),
        **records,
        "persisted_comparison": comparison,
        "paired_outer_speedup": (
            float(records["trusted_pre_s1"]["outer_create_wall_seconds"])
            / float(records["promoted_s1"]["outer_create_wall_seconds"])
        ),
    }


def run_field_experiment(
    root: Path,
    cache_root: Path,
    repetitions: int,
    samples: int,
    duration: float,
) -> dict[str, object]:
    pairs = [
        run_field_pair(
            root / f"pair-{index + 1}",
            cache_root / f"pair-{index + 1}",
            PAIR_ORDERS[index],
            samples,
            duration,
        )
        for index in range(repetitions)
    ]
    promoted_walls = [
        float(pair["promoted_s1"]["outer_create_wall_seconds"])
        for pair in pairs
    ]
    return {
        "pairs": pairs,
        "median_promoted_outer_wall_seconds": statistics.median(promoted_walls),
        "all_comparisons_accepted": all(
            bool(pair["persisted_comparison"]["accepted"]) for pair in pairs
        ),
        "all_workers_stopped": all(
            bool(pair[label]["all_workers_stopped"])
            for pair in pairs
            for label in ("promoted_s1", "trusted_pre_s1")
        ),
    }


def _baseline() -> dict[str, object]:
    payload = json.loads(BASELINE_EVIDENCE.read_text())
    promoted = payload["promoted_s1"]
    return {
        "source": str(BASELINE_EVIDENCE),
        "promoted_outer_wall_seconds": promoted["outer_create_wall_seconds"],
        "promoted_setup_seconds": promoted["setup_seconds"],
        "promoted_maximum_worker_peak_rss_bytes": promoted[
            "maximum_worker_peak_rss_bytes"
        ],
        "trusted_outer_wall_seconds": payload["trusted_pre_s1"][
            "outer_create_wall_seconds"
        ],
    }


def run_acceptance(
    work_directory: Path,
    *,
    lifecycle_repetitions: int,
    field_repetitions: int,
    samples: int,
    duration: float,
) -> dict[str, object]:
    support = s1_build_support()
    spec = RenormalizedTangentSpec(duration=duration)
    eligibility = s1_specification_eligibility(spec)
    if not support.supported or not eligibility.eligible:
        raise RuntimeError(
            f"Acceptance environment/specification is unsupported: {support}; {eligibility}"
        )
    baseline = _baseline()
    lifecycle = run_lifecycle_experiment(
        work_directory / "lifecycle-cache",
        lifecycle_repetitions,
    )
    field = run_field_experiment(
        work_directory / "fields",
        work_directory / "field-cache",
        field_repetitions,
        samples,
        duration,
    )
    setup_improvement = 1.0 - (
        float(lifecycle["median_effective_eight_pool_setup_seconds"])
        / float(baseline["promoted_setup_seconds"])
    )
    wall_improvement = 1.0 - (
        float(field["median_promoted_outer_wall_seconds"])
        / float(baseline["promoted_outer_wall_seconds"])
    )
    peak_rss = max(
        int(pair["promoted_s1"]["maximum_worker_peak_rss_bytes"])
        for pair in field["pairs"]
    )
    rss_ratio = peak_rss / int(baseline["promoted_maximum_worker_peak_rss_bytes"])
    gates = {
        "setup_improvement_fraction": setup_improvement,
        "setup_at_least_40_percent_lower": setup_improvement >= 0.40,
        "field_wall_improvement_fraction": wall_improvement,
        "field_wall_at_least_20_percent_lower": wall_improvement >= 0.20,
        "scientific_comparisons_accepted": field["all_comparisons_accepted"],
        "all_workers_stopped": field["all_workers_stopped"]
        and all(
            bool(record["all_workers_stopped"])
            for record in lifecycle["repetitions"]
        ),
        "maximum_promoted_worker_peak_rss_bytes": peak_rss,
        "rss_ratio_to_established_promoted_baseline": rss_ratio,
        "rss_increase_no_more_than_10_percent": rss_ratio <= 1.10,
    }
    gates["accepted"] = all(
        (
            gates["setup_at_least_40_percent_lower"],
            gates["field_wall_at_least_20_percent_lower"],
            gates["scientific_comparisons_accepted"],
            gates["all_workers_stopped"],
            gates["rss_increase_no_more_than_10_percent"],
        )
    )
    sources = (
        Path(__file__),
        PROTOTYPE_DIRECTORY / "src" / "lyapunov" / "s1.py",
        PROTOTYPE_DIRECTORY / "src" / "lyapunov" / "s1_artifacts.py",
        PROTOTYPE_DIRECTORY / "src" / "lyapunov" / "field_adapter.py",
        PROTOTYPE_DIRECTORY / "src" / "generation" / "runner.py",
    )
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "build-once/load-many S1 bounded acceptance",
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "numba": numba.__version__,
            "git_head": _git_output("rev-parse", "HEAD"),
            "git_status_short_before_artifact": _git_output("status", "--short"),
            "s1_build": s1_build_provenance(),
        },
        "workload": {
            "samples_per_axis": samples,
            "duration_seconds": duration,
            "lifecycle_repetitions": lifecycle_repetitions,
            "field_repetitions": field_repetitions,
            "pair_orders": [list(order) for order in PAIR_ORDERS[:field_repetitions]],
            "multiprocessing_policy": asdict(accepted_process_execution_spec()),
        },
        "baseline": baseline,
        "lifecycle": lifecycle,
        "field": field,
        "acceptance_gates": gates,
        "source_sha256": {str(path): _sha256(path) for path in sources},
    }


def save(payload: Mapping[str, object], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as target:
        json.dump(payload, target, indent=2, sort_keys=True, allow_nan=False)
        target.write("\n")
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--lifecycle-repetitions", type=int, default=3)
    parser.add_argument("--field-repetitions", type=int, default=3)
    parser.add_argument("--samples-per-axis", type=int, default=128)
    parser.add_argument("--duration", type=float, default=5.0)
    parser.add_argument("--work-directory", type=Path)
    return parser


def main(arguments: list[str] | None = None) -> int:
    options = build_parser().parse_args(arguments)
    if options.output.exists():
        raise FileExistsError(f"Refusing to replace benchmark: {options.output}")
    if not 1 <= options.field_repetitions <= len(PAIR_ORDERS):
        raise ValueError("field-repetitions must be between one and three")
    if options.lifecycle_repetitions <= 0:
        raise ValueError("lifecycle-repetitions must be positive")
    if options.samples_per_axis <= 0 or options.duration <= 0:
        raise ValueError("field size and duration must be positive")
    if options.work_directory is None:
        with tempfile.TemporaryDirectory(prefix="s1-artifact-acceptance-") as name:
            payload = run_acceptance(
                Path(name),
                lifecycle_repetitions=options.lifecycle_repetitions,
                field_repetitions=options.field_repetitions,
                samples=options.samples_per_axis,
                duration=options.duration,
            )
    else:
        options.work_directory.mkdir(parents=True, exist_ok=False)
        payload = run_acceptance(
            options.work_directory,
            lifecycle_repetitions=options.lifecycle_repetitions,
            field_repetitions=options.field_repetitions,
            samples=options.samples_per_axis,
            duration=options.duration,
        )
    save(payload, options.output)
    print(json.dumps(payload["acceptance_gates"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
